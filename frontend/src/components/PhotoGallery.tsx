import { useState } from "react";
import type { GamePhoto } from "../api";

type PhotoGalleryProps = {
  photos: GamePhoto[];
  canDelete?: boolean;
  onDelete?: (photoId: number) => Promise<void>;
  compact?: boolean;
};

export default function PhotoGallery({
  photos,
  canDelete = false,
  onDelete,
  compact = false,
}: PhotoGalleryProps) {
  const [lightbox, setLightbox] = useState<GamePhoto | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  if (!photos.length) {
    return <p className="muted">No photos yet.</p>;
  }

  async function handleDelete(photoId: number) {
    if (!onDelete) return;
    setDeletingId(photoId);
    try {
      await onDelete(photoId);
      if (lightbox?.id === photoId) setLightbox(null);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <div className={`photo-grid${compact ? " photo-grid--compact" : ""}`}>
        {photos.map((photo) => (
          <figure key={photo.id} className="photo-grid__item">
            <button
              type="button"
              className="photo-grid__thumb"
              onClick={() => setLightbox(photo)}
              aria-label={photo.caption || "View photo"}
            >
              <img src={photo.url} alt={photo.caption || "Game photo"} loading="lazy" />
            </button>
            {!compact && photo.caption && <figcaption className="muted">{photo.caption}</figcaption>}
            {canDelete && onDelete && (
              <button
                type="button"
                className="btn secondary btn--sm photo-grid__delete"
                disabled={deletingId === photo.id}
                onClick={() => handleDelete(photo.id)}
              >
                {deletingId === photo.id ? "Deleting…" : "Delete"}
              </button>
            )}
          </figure>
        ))}
      </div>

      {lightbox && (
        <div
          className="feedback-modal-overlay"
          role="presentation"
          onClick={() => setLightbox(null)}
        >
          <div
            className="photo-lightbox"
            role="dialog"
            aria-modal="true"
            aria-label="Photo preview"
            onClick={(e) => e.stopPropagation()}
          >
            <img src={lightbox.url} alt={lightbox.caption || "Game photo"} />
            <div className="photo-lightbox__meta">
              {lightbox.caption && <p>{lightbox.caption}</p>}
              <p className="muted">
                {lightbox.uploaded_by_name} · {new Date(lightbox.created_at).toLocaleString()}
              </p>
            </div>
            <button type="button" className="btn secondary" onClick={() => setLightbox(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
