import { useState, lazy, Suspense } from "react";
import "./App.css";
import TabBar from "./components/TabBar";
import OverviewTab from "./components/OverviewTab";
import ChatWidget from "./components/ChatWidget";

const DetailedDataTab = lazy(() => import("./components/DetailedDataTab"));
const DataTab = lazy(() => import("./components/DataTab"));

const TABS = ["Overview", "Detailed Data", "Database"];

export default function App() {
  const [activeTab, setActiveTab] = useState("Overview");

  return (
    <div className="app">
      <TabBar tabs={TABS} active={activeTab} onSelect={setActiveTab} />
      <Suspense fallback={<div className="tab-loading">Loading...</div>}>
        {activeTab === "Overview" && <OverviewTab />}
        {activeTab === "Detailed Data" && <DetailedDataTab />}
        {activeTab === "Database" && <DataTab />}
      </Suspense>
      <ChatWidget />
    </div>
  );
}
