export default function TabBar({ tabs, active, onSelect }) {
  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <button
          key={tab}
          className={`tab-btn${active === tab ? " active" : ""}`}
          onClick={() => onSelect(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
