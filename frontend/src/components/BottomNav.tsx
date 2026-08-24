import { NavLink } from "react-router-dom";

const items = [
  { to: "/", label: "Start", icon: "■", end: true },
  { to: "/tiere", label: "Tiere", icon: "●" },
  { to: "/rassen", label: "Rassen", icon: "◆" },
  { to: "/stallplan", label: "Stallplan", icon: "▦" },
  { to: "/futter", label: "Futter", icon: "▲" },
  { to: "/scan", label: "Scan", icon: "◈" },
  { to: "/konto", label: "Konto", icon: "◐" },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? "active" : "")}>
          <span className="nav-icon">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
