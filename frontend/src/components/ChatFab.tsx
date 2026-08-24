import { Link, useLocation } from "react-router-dom";

function ChatBubbleIcon({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 4h16v12H8l-4 4V4Z" />
      <path d="M8 9h8M8 12.5h5" />
    </svg>
  );
}

export function ChatFab() {
  const location = useLocation();
  if (location.pathname === "/chat") return null;
  return (
    <Link className="chat-fab" to="/chat" aria-label="Zucht-Assistent öffnen" title="Zucht-Assistent">
      <ChatBubbleIcon />
    </Link>
  );
}
