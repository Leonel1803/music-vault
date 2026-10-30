import React from "react";
import ReactDOM from "react-dom/client";
import { Amplify } from "aws-amplify";
import { AuthProvider } from "./context/AuthContext";
import { App } from "./App";
import "./styles.css";

const {
  VITE_COGNITO_USER_POOL_ID,
  VITE_COGNITO_USER_POOL_CLIENT_ID,
  VITE_COGNITO_DOMAIN,
  VITE_COGNITO_REDIRECT_SIGN_IN,
  VITE_COGNITO_REDIRECT_SIGN_OUT,
} = import.meta.env;

if (VITE_COGNITO_USER_POOL_ID && VITE_COGNITO_USER_POOL_CLIENT_ID && VITE_COGNITO_DOMAIN) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: VITE_COGNITO_USER_POOL_ID,
        userPoolClientId: VITE_COGNITO_USER_POOL_CLIENT_ID,
        loginWith: {
          oauth: {
            domain: VITE_COGNITO_DOMAIN,
            scopes: ["openid", "email", "profile"],
            redirectSignIn: [VITE_COGNITO_REDIRECT_SIGN_IN || window.location.origin],
            redirectSignOut: [VITE_COGNITO_REDIRECT_SIGN_OUT || window.location.origin],
            responseType: "code",
          },
        },
      },
    },
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider><App /></AuthProvider>
  </React.StrictMode>,
);
