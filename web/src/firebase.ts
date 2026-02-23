import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const DEFAULT_CONFIG = {
  apiKey: "AIzaSyCRPmK9euOr_rDVcQDBh_BC9OVM2MnJF0s",
  authDomain: "living-memories-488001.firebaseapp.com",
  projectId: "living-memories-488001",
  appId: "1:404986156809:web:47877e11168d63a32965d8",
};

const config = import.meta.env.VITE_FIREBASE_CONFIG
  ? JSON.parse(import.meta.env.VITE_FIREBASE_CONFIG)
  : DEFAULT_CONFIG;

export const firebaseApp = initializeApp(config);
export const auth = getAuth(firebaseApp);
