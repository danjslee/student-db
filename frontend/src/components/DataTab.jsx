import { useState } from "react";
import TabBar from "./TabBar";
import StudentsGrid from "./StudentsGrid";
import ProductsGrid from "./ProductsGrid";
import EnrollmentsGrid from "./EnrollmentsGrid";
import SalesGrid from "./SalesGrid";
import ScholarshipsGrid from "./ScholarshipsGrid";

const SUB_TABS = ["Students", "Products", "Enrollments", "Sales", "Scholarships"];

export default function DataTab() {
  const [activeTab, setActiveTab] = useState("Students");

  return (
    <>
      <TabBar tabs={SUB_TABS} active={activeTab} onSelect={setActiveTab} />
      {activeTab === "Students" && <StudentsGrid />}
      {activeTab === "Products" && <ProductsGrid />}
      {activeTab === "Enrollments" && <EnrollmentsGrid />}
      {activeTab === "Sales" && <SalesGrid />}
      {activeTab === "Scholarships" && <ScholarshipsGrid />}
    </>
  );
}
