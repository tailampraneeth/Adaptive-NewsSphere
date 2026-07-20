import React from 'react';
import { Outlet } from 'react-router-dom';
import TopBar from '../components/TopBar';
import BottomNav from '../components/BottomNav';
import './MainLayout.css';

export const MainLayout = () => {
  return (
    <div className="main-layout-container">
      <TopBar />
      <div className="main-layout-body">
        <main className="main-content-area">
          <div className="main-content-scroll">
            <Outlet />
          </div>
        </main>
      </div>
      <BottomNav />
    </div>
  );
};
export default MainLayout;
