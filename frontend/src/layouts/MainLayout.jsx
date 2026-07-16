import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import './MainLayout.css';

export const MainLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="main-layout-container">
      <Navbar onToggleSidebar={toggleSidebar} />
      <div className="main-layout-body">
        <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />
        <main className="main-content-area" onClick={closeSidebar}>
          <div className="main-content-scroll">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
export default MainLayout;
