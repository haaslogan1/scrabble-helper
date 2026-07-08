type AvatarProps = {
  name: string;
  email?: string;
  avatarUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const SIZE_CLASS = {
  sm: "avatar--sm",
  md: "avatar--md",
  lg: "avatar--lg",
} as const;

export default function Avatar({
  name,
  email,
  avatarUrl,
  size = "md",
  className = "",
}: AvatarProps) {
  const initial = (name || email || "?").charAt(0).toUpperCase();
  const classes = `avatar ${SIZE_CLASS[size]} ${className}`.trim();

  if (avatarUrl) {
    return (
      <img
        className={classes}
        src={avatarUrl}
        alt=""
        aria-hidden="true"
      />
    );
  }

  return (
    <span className={classes} aria-hidden="true">
      {initial}
    </span>
  );
}
