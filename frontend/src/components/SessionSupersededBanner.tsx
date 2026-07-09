import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { consumeSessionSuperseded } from "../auth/AuthContext";

export default function SessionSupersededBanner() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!consumeSessionSuperseded()) return;
    window.alert("You were signed out because you signed in on another device.");
    navigate("/login", { replace: true });
  }, [navigate]);

  return null;
}
