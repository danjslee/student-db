import { useState } from "react";
import TabBar from "./TabBar";
import StudentsGrid from "./StudentsGrid";
import ProductsGrid from "./ProductsGrid";
import EnrollmentsGrid from "./EnrollmentsGrid";
import SalesGrid from "./SalesGrid";
import ScholarshipsGrid from "./ScholarshipsGrid";
import BroadcastsGrid from "./BroadcastsGrid";
import EmailSendsGrid from "./EmailSendsGrid";

const SUB_TABS = ["Students", "Products", "Enrollments", "Sales", "Scholarships", "Course Emails", "Email Sends"];

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
      {activeTab === "Course Emails" && <BroadcastsGrid />}
      {activeTab === "Email Sends" && <EmailSendsGrid />}
    </>
  );
}
