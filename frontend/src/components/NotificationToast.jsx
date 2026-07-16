import React from 'react';
import useNotification from '../hooks/useNotification';
import './NotificationToast.css';

export const NotificationToast = () => {
  const { notifications, removeNotification } = useNotification();

  if (notifications.length === 0) return null;

  return (
    <div className="toast-area" aria-live="assertive">
      {notifications.map((toast) => (
        <div key={toast.id} className={`toast-card toast-${toast.type} animate-slide-up`}>
          <span className="toast-text">{toast.message}</span>
          <button
            className="toast-close"
            onClick={() => removeNotification(toast.id)}
            aria-label="Dismiss Alert"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
};
export default NotificationToast;
