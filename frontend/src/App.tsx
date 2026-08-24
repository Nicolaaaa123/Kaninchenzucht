import { BrowserRouter, Route, Routes } from "react-router-dom";
import { BottomNav } from "./components/BottomNav";
import { ChatFab } from "./components/ChatFab";
import { MoonIcon, SunIcon } from "./components/Icons";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { useTheme } from "./hooks/useTheme";
import { Account } from "./pages/Account";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Animals } from "./pages/Animals";
import { AnimalNew } from "./pages/AnimalNew";
import { AnimalDetail } from "./pages/AnimalDetail";
import { AnimalLabel } from "./pages/AnimalLabel";
import { AnimalLabels } from "./pages/AnimalLabels";
import { Breeds } from "./pages/Breeds";
import { StallPlan } from "./pages/StallPlan";
import { Feeds } from "./pages/Feeds";
import { ScanEvaluationCard } from "./pages/ScanEvaluationCard";
import { Compare } from "./pages/Compare";
import { MatingSuggestions } from "./pages/MatingSuggestions";
import { Chat } from "./pages/Chat";
import { BluetoothScan } from "./pages/BluetoothScan";
import { LitterNew } from "./pages/LitterNew";
import { StallLabels } from "./pages/StallLabels";
import { YearlyStats } from "./pages/YearlyStats";

function AppShell() {
  const { theme, toggleTheme } = useTheme();
  const { user, loading } = useAuth();

  if (loading) return null;
  if (!user) return <Login />;

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="logo-mark">K</span>
        Kaninchenzucht
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          title={theme === "dark" ? "Helles Design" : "Dunkles Design"}
          aria-label={theme === "dark" ? "Helles Design aktivieren" : "Dunkles Design aktivieren"}
        >
          {theme === "dark" ? <SunIcon size={17} /> : <MoonIcon size={17} />}
        </button>
      </header>
      <BottomNav />
      <ChatFab />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tiere" element={<Animals />} />
          <Route path="/tiere/neu" element={<AnimalNew />} />
          <Route path="/tiere/etiketten" element={<AnimalLabels />} />
          <Route path="/tiere/vergleich" element={<Compare />} />
          <Route path="/tiere/wurf" element={<LitterNew />} />
          <Route path="/tiere/:id" element={<AnimalDetail />} />
          <Route path="/tiere/:id/etikett" element={<AnimalLabel />} />
          <Route path="/tiere/:id/paarung" element={<MatingSuggestions />} />
          <Route path="/rassen" element={<Breeds />} />
          <Route path="/stallplan" element={<StallPlan />} />
          <Route path="/stallplan/etiketten" element={<StallLabels />} />
          <Route path="/futter" element={<Feeds />} />
          <Route path="/scan" element={<ScanEvaluationCard />} />
          <Route path="/chip-scanner" element={<BluetoothScan />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/statistik" element={<YearlyStats />} />
          <Route path="/konto" element={<Account />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
