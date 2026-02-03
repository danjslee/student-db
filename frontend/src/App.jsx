import { useState } from "react";
import "./App.css";
import TabBar from "./components/TabBar";
import InsightsTab from "./components/InsightsTab";
import DataTab from "./components/DataTab";
import ChatTab from "./components/ChatTab";

const TABS = ["Insights & Charts", "Data", "Chat"];

export default function App() {
  const [activeTab, setActiveTab] = useState("Insights & Charts");

  return (
    <div className="app">
      <TabBar tabs={TABS} active={activeTab} onSelect={setActiveTab} />
      {activeTab === "Insights & Charts" && <InsightsTab />}
      {activeTab === "Data" && <DataTab />}
      {activeTab === "Chat" && <ChatTab />}
    </div>
  );
}
