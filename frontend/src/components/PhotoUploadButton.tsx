import { useState } from "react";

type PhotoUploadButtonProps = {
  label?: string;
  disabled?: boolean;
  onUpload: (file: File) => Promise<void>;
};

export default function PhotoUploadButton({
  label = "Upload photo",
  disabled = false,
  onUpload,
}: PhotoUploadButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      await onUpload(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="photo-upload">
      <label className={`btn secondary${busy || disabled ? " btn--disabled" : ""}`}>
        {busy ? "Uploading…" : label}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          disabled={busy || disabled}
          onChange={onChange}
        />
      </label>
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
