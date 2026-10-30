import io
import json
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

from src.catalog import handle_catalog
from src.common import (
    ApiError,
    clean_text,
    decode_cursor,
    emit_metrics,
    encode_cursor,
    page_size,
    parse_rating,
    public_item,
    user_sub,
    validate_id,
)
from src.interactions import handle_interactions
from src.library import handle_library


class FakeTable:
    def __init__(self):
        self.query_calls = []
        self.get_calls = []
        self.put_calls = []
        self.delete_calls = []
        self.update_calls = []
        self.query_result = {"Items": []}
        self.get_result = {}
        self.put_old = None
        self.delete_old = None
        self.update_result = {"Attributes": {}}

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return self.query_result

    def get_item(self, **kwargs):
        self.get_calls.append(kwargs)
        return self.get_result

    def put_item(self, **kwargs):
        self.put_calls.append(kwargs)
        return {"Attributes": self.put_old} if self.put_old else {}

    def delete_item(self, **kwargs):
        self.delete_calls.append(kwargs)
        return {"Attributes": self.delete_old} if self.delete_old else {}

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)
        return self.update_result


def event(method, path, *, query=None, sub=None, body=None):
    claims = {"sub": sub} if sub else {}
    return {
        "rawPath": path,
        "queryStringParameters": query or {},
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": claims}},
        },
    }


class CommonTests(unittest.TestCase):
    def test_cursor_round_trip(self):
        key = {"PK": "SONG#one", "SK": "METADATA"}
        self.assertEqual(decode_cursor(encode_cursor(key)), key)
        self.assertIsNone(decode_cursor(None))

    def test_invalid_page_size_and_cursor_are_rejected(self):
        with self.assertRaises(ApiError):
            page_size({"limit": "101"})
        with self.assertRaises(ApiError):
            decode_cursor("not-json")

    def test_identifier_is_validated(self):
        self.assertEqual(validate_id("song_1"), "song_1")
        with self.assertRaises(ApiError):
            validate_id("../song")

    def test_private_request_requires_verified_subject(self):
        self.assertEqual(user_sub(event("GET", "/me/library", sub="user-1")), "user-1")
        with self.assertRaises(ApiError) as error:
            user_sub(event("GET", "/me/library"))
        self.assertEqual(error.exception.status_code, 401)

    def test_api_json_keeps_dynamodb_numbers_numeric(self):
        from src.common import response

        payload = json.loads(response(200, {"durationSeconds": Decimal("12.5")})["body"])
        self.assertEqual(payload["durationSeconds"], 12.5)


class CatalogTests(unittest.TestCase):
    def test_song_search_uses_index_and_cursor(self):
        table = FakeTable()
        cursor = encode_cursor({"GSI1PK": "ENTITY#SONG", "GSI1SK": "blue#song-1"})
        result = handle_catalog(event(
            "GET", "/songs", query={"q": " Blue ", "limit": "10", "cursor": cursor}
        ), table)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(table.query_calls[0]["IndexName"], "GSI1")
        self.assertEqual(table.query_calls[0]["ExpressionAttributeValues"][":prefix"], "blue")
        self.assertEqual(table.query_calls[0]["ExclusiveStartKey"]["GSI1SK"], "blue#song-1")

    def test_genre_filter_queries_partition_key(self):
        table = FakeTable()
        handle_catalog(event("GET", "/songs", query={"genre": "Jazz"}), table)
        self.assertEqual(table.query_calls[0]["IndexName"], "GSI1")
        self.assertEqual(table.query_calls[0]["ExpressionAttributeValues"][":pk"], "GENRE#jazz")

    def test_global_search_applies_genre_to_song_partition(self):
        table = FakeTable()
        handle_catalog(event("GET", "/search", query={"q": "bl", "genre": "Jazz"}), table)
        song_query = table.query_calls[2]
        self.assertEqual(song_query["ExpressionAttributeValues"][":pk"], "GENRE#jazz")
        self.assertEqual(song_query["ExpressionAttributeValues"][":prefix"], "bl")

    def test_search_combines_entity_types(self):
        table = FakeTable()
        table.query_result = {"Items": [{"title": "Blue"}]}
        result = handle_catalog(event("GET", "/search", query={"q": "bl"}), table)
        self.assertEqual(len(table.query_calls), 3)
        self.assertEqual(json.loads(result["body"])["items"][0]["entityType"], "artists")

    def test_detail_returns_not_found(self):
        with self.assertRaises(ApiError) as error:
            handle_catalog(event("GET", "/songs/unknown"), FakeTable())
        self.assertEqual(error.exception.status_code, 404)


class PersonalTests(unittest.TestCase):
    def test_favorite_is_scoped_to_jwt_subject(self):
        table = FakeTable()
        table.get_result = {"Item": {"title": "T", "artistName": "A"}}
        result = handle_interactions(event("PUT", "/me/favorites/song-1", sub="user-7"), table)
        self.assertEqual(result["statusCode"], 204)
        item = table.put_calls[0]["Item"]
        self.assertEqual(item["PK"], "USER#user-7")
        self.assertEqual(item["SK"], "FAVORITE#song-1")
        self.assertEqual(item["title"], "T")

    def test_list_library_paginates(self):
        table = FakeTable()
        table.query_result = {"Items": [{"PK": "USER#u", "SK": "LIBRARY#s1", "songId": "s1"}],
                              "LastEvaluatedKey": {"PK": "USER#u"}}
        result = handle_library(event("GET", "/me/library", query={"limit": "5"}, sub="u"), table)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(table.query_calls[0]["ExpressionAttributeValues"][":prefix"], "LIBRARY#")
        body = json.loads(result["body"])
        self.assertEqual(body["items"], [{"songId": "s1"}])
        self.assertTrue(body["nextCursor"])

    def test_library_rejects_other_resources(self):
        with self.assertRaises(ApiError) as error:
            handle_library(event("GET", "/me/favorites", sub="u"), FakeTable())
        self.assertEqual(error.exception.status_code, 404)

    def test_missing_authentication_is_rejected(self):
        with self.assertRaises(ApiError) as error:
            handle_interactions(event("GET", "/me/favorites"), FakeTable())
        self.assertEqual(error.exception.status_code, 401)


class RatingTests(unittest.TestCase):
    def test_first_rating_adds_to_summary(self):
        table = FakeTable()
        table.get_result = {"Item": {"id": "s1"}}
        table.update_result = {"Attributes": {"ratingSum": Decimal(4), "ratingCount": Decimal(1)}}
        result = handle_interactions(
            event("PUT", "/me/ratings/s1", sub="u1", body={"rating": 4}), table)
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(table.put_calls[0]["Item"]["SK"], "RATING#u1")
        values = table.update_calls[0]["ExpressionAttributeValues"]
        self.assertEqual((values[":total"], values[":count"]), (4, 1))
        self.assertEqual((body["ratingAverage"], body["ratingCount"]), (4.0, 1))

    def test_changing_rating_only_applies_the_difference(self):
        table = FakeTable()
        table.get_result = {"Item": {"id": "s1"}}
        table.put_old = {"rating": Decimal(2)}
        handle_interactions(event("PUT", "/me/ratings/s1", sub="u1", body={"rating": 5}), table)
        values = table.update_calls[0]["ExpressionAttributeValues"]
        self.assertEqual((values[":total"], values[":count"]), (3, 0))

    def test_removing_rating_reverts_summary(self):
        table = FakeTable()
        table.delete_old = {"rating": Decimal(3)}
        result = handle_interactions(event("DELETE", "/me/ratings/s1", sub="u1"), table)
        values = table.update_calls[0]["ExpressionAttributeValues"]
        self.assertEqual(result["statusCode"], 204)
        self.assertEqual((values[":total"], values[":count"]), (-3, -1))

    def test_invalid_ratings_are_rejected(self):
        for bad in (0, 6, "5", 3.5, True, None):
            with self.assertRaises(ApiError):
                parse_rating(bad)
        self.assertEqual(parse_rating(5), 5)

    def test_rating_unknown_song_returns_not_found(self):
        with self.assertRaises(ApiError) as error:
            handle_interactions(event("PUT", "/me/ratings/s1", sub="u", body={"rating": 3}), FakeTable())
        self.assertEqual(error.exception.status_code, 404)


class ReviewTests(unittest.TestCase):
    def test_review_is_stored_under_jwt_subject_and_sanitized(self):
        table = FakeTable()
        table.get_result = {"Item": {"id": "s1"}}
        table.update_result = {"Attributes": {
            "PK": "SONG#s1", "SK": "REVIEW#u1", "text": "Genial", "authorName": "Ana"}}
        result = handle_interactions(event(
            "PUT", "/me/reviews/s1", sub="u1",
            body={"text": " Genial\x00 ", "authorName": "Ana", "SK": "REVIEW#otro"}), table)
        call = table.update_calls[0]
        self.assertEqual(call["Key"], {"PK": "SONG#s1", "SK": "REVIEW#u1"})
        self.assertEqual(call["ExpressionAttributeValues"][":text"], "Genial")
        self.assertEqual(json.loads(result["body"])["item"], {"text": "Genial", "authorName": "Ana"})

    def test_review_text_limits(self):
        with self.assertRaises(ApiError):
            clean_text("   ", "text", min_length=1, max_length=10)
        with self.assertRaises(ApiError):
            clean_text("x" * 11, "text", min_length=1, max_length=10)
        with self.assertRaises(ApiError):
            clean_text(5, "text", min_length=1, max_length=10)

    def test_review_requires_body(self):
        with self.assertRaises(ApiError) as error:
            handle_interactions(event("PUT", "/me/reviews/s1", sub="u"), FakeTable())
        self.assertEqual(error.exception.status_code, 400)

    def test_public_review_list_hides_keys_and_author_identity(self):
        table = FakeTable()
        table.query_result = {"Items": [{
            "PK": "SONG#s1", "SK": "REVIEW#secret-sub", "songId": "s1", "text": "ok",
            "authorName": "Ana", "createdAt": "2026-01-01T00:00:00+00:00"}]}
        result = handle_catalog(event("GET", "/songs/s1/reviews", query={"limit": "5"}), table)
        call = table.query_calls[0]
        self.assertEqual(call["ExpressionAttributeValues"], {":pk": "SONG#s1", ":prefix": "REVIEW#"})
        self.assertNotIn("secret-sub", result["body"])
        self.assertNotIn("PK", json.loads(result["body"])["items"][0])


class SerializationTests(unittest.TestCase):
    def test_internal_keys_are_removed(self):
        item = public_item({"PK": "SONG#1", "SK": "METADATA", "GSI1PK": "x", "GSI1SK": "y", "id": "1"})
        self.assertEqual(set(item), {"id", "ratingAverage", "ratingCount"})

    def test_song_rating_average_is_derived(self):
        item = public_item({"PK": "SONG#1", "SK": "METADATA", "ratingSum": Decimal(9), "ratingCount": Decimal(2)})
        self.assertEqual((item["ratingAverage"], item["ratingCount"]), (4.5, 2))
        self.assertNotIn("ratingSum", item)

    def test_non_song_items_have_no_rating_fields(self):
        self.assertEqual(public_item({"PK": "ARTIST#1", "SK": "METADATA", "name": "A"}), {"name": "A"})

    def test_catalog_responses_never_include_key_attributes(self):
        table = FakeTable()
        table.query_result = {"Items": [{"PK": "ARTIST#1", "SK": "METADATA", "GSI1PK": "ENTITY#ARTIST",
                                         "GSI1SK": "a#1", "id": "1", "name": "A"}]}
        body = json.loads(handle_catalog(event("GET", "/artists"), table)["body"])
        self.assertEqual(body["items"], [{"id": "1", "name": "A"}])
        table.get_result = {"Item": {"PK": "SONG#1", "SK": "METADATA", "id": "1", "title": "T"}}
        detail = json.loads(handle_catalog(event("GET", "/songs/1"), table)["body"])["item"]
        self.assertEqual(detail, {"id": "1", "title": "T", "ratingAverage": None, "ratingCount": 0})


class RelationTests(unittest.TestCase):
    def test_albums_of_artist(self):
        table = FakeTable()
        handle_catalog(event("GET", "/artists/a1/albums"), table)
        self.assertEqual(table.query_calls[0]["ExpressionAttributeValues"], {":pk": "ARTIST#a1", ":prefix": "ALBUM#"})

    def test_songs_of_album(self):
        table = FakeTable()
        handle_catalog(event("GET", "/albums/al1/songs"), table)
        self.assertEqual(table.query_calls[0]["ExpressionAttributeValues"], {":pk": "ALBUM#al1", ":prefix": "SONG#"})

    def test_unknown_relation_is_not_found(self):
        with self.assertRaises(ApiError):
            handle_catalog(event("GET", "/songs/s1/albums"), FakeTable())
        with self.assertRaises(ApiError):
            handle_catalog(event("GET", "/artists/../albums"), FakeTable())


class MetricsTests(unittest.TestCase):
    def capture(self, **kwargs):
        stream = io.StringIO()
        with redirect_stdout(stream):
            emit_metrics("catalog", **kwargs)
        return json.loads(stream.getvalue())

    def test_embedded_metric_format_record(self):
        record = self.capture(status_code=200, latency_ms=12.345)
        directive = record["_aws"]["CloudWatchMetrics"][0]
        self.assertEqual(directive["Namespace"], "MusicVault")
        self.assertEqual(directive["Dimensions"], [["Service"]])
        self.assertEqual({m["Name"] for m in directive["Metrics"]}, {"Requests", "ServerErrors", "LatencyMs"})
        self.assertEqual((record["Service"], record["Requests"], record["ServerErrors"]), ("catalog", 1, 0))

    def test_server_errors_and_contributions(self):
        record = self.capture(status_code=500, latency_ms=1, contributions=1)
        self.assertEqual((record["ServerErrors"], record["Contributions"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
