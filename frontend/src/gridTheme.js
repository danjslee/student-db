import { themeAlpine, colorSchemeDarkWarm } from "ag-grid-community";

export const darkTheme = themeAlpine.withPart(colorSchemeDarkWarm).withParams({
  backgroundColor: "#1c1917",
  foregroundColor: "#ffffff",
  borderColor: "#292524",
  headerBackgroundColor: "#292524",
  rowHoverColor: "#29252480",
  selectedRowBackgroundColor: "#44403c",
  headerTextColor: "#d6d3d1",
});
