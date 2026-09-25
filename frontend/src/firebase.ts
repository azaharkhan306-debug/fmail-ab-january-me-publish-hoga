// Firebase JS SDK — configured for Fmail (project fmail-a296f).
// Firebase is initialized app-wide. Auth is handled by the Fmail backend (JWT);
// Firebase app is available here for future Firebase-native features.
import { initializeApp, getApps, getApp } from "firebase/app";

export const firebaseConfig = {
  apiKey: "AIzaSyAALKyCH-jYBFCbeubfNZ-DeUePMrwhtQ0",
  authDomain: "fmail-a296f.firebaseapp.com",
  projectId: "fmail-a296f",
  storageBucket: "fmail-a296f.firebasestorage.app",
  messagingSenderId: "1022499911639",
  appId: "1:1022499911639:android:f7805af1a2380d76ab3d92",
};

export const firebaseApp = getApps().length ? getApp() : initializeApp(firebaseConfig);
