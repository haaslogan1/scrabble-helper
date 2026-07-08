import { useCallback, useEffect, useState } from "react";
import {
  deleteGamePhoto,
  listGamePhotos,
  uploadGamePhoto,
  type GamePhoto,
} from "../api";
import PhotoGallery from "./PhotoGallery";
import PhotoUploadButton from "./PhotoUploadButton";

type GamePhotoSectionProps = {
  gameId: number;
  isOwner: boolean;
  compact?: boolean;
};

export default function GamePhotoSection({
  gameId,
  isOwner,
  compact = false,
}: GamePhotoSectionProps) {
  const [photos, setPhotos] = useState<GamePhoto[]>([]);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    listGamePhotos(gameId)
      .then(setPhotos)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [gameId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onUpload(file: File) {
    await uploadGamePhoto(gameId, file, { context: "board" });
    refresh();
  }

  async function onDelete(photoId: number) {
    await deleteGamePhoto(gameId, photoId);
    refresh();
  }

  return (
    <div className="card">
      <div className="section-header">
        <h2>Board photos</h2>
        {isOwner && <PhotoUploadButton label="Add photo" onUpload={onUpload} />}
      </div>
      {error && <p className="error-text">{error}</p>}
      <PhotoGallery
        photos={photos}
        canDelete={isOwner}
        onDelete={isOwner ? onDelete : undefined}
        compact={compact}
      />
    </div>
  );
}
