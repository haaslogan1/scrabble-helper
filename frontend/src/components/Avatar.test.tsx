import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Avatar from "./Avatar";

afterEach(() => {
  cleanup();
});

describe("Avatar", () => {
  it("renders an img with avatar size classes when avatarUrl is set", () => {
    const { container } = render(
      <Avatar
        name="Logan"
        avatarUrl="https://lh3.googleusercontent.com/a/example=s96-c"
        size="sm"
      />,
    );
    const img = container.querySelector("img.avatar.avatar--sm");
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute("src", "https://lh3.googleusercontent.com/a/example=s96-c");
  });

  it("renders a letter span when avatarUrl is missing", () => {
    const { container } = render(<Avatar name="Chris" size="sm" />);
    const span = container.querySelector("span.avatar.avatar--sm");
    expect(span).not.toBeNull();
    expect(span).toHaveTextContent("C");
    expect(container.querySelector("img")).toBeNull();
  });
});
