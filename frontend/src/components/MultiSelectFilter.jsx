import { colors } from "../chartTheme";

export default function MultiSelectFilter({ items, selected, onToggle, label }) {
  return (
    <div className="multi-select-filter">
      {label && <span className="filter-label">{label}</span>}
      <div className="filter-chips">
        {items.map((item) => {
          const isSelected = selected.includes(item.id);
          return (
            <button
              key={item.id}
              className={`filter-chip${isSelected ? " selected" : ""}`}
              onClick={() => onToggle(item.id)}
              style={isSelected ? { backgroundColor: colors.primary, borderColor: colors.primary, color: "#fff" } : {}}
            >
              {item.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
