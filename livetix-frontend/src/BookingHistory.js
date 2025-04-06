import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './BookingHistory.css';

function BookingHistory() {
  const [bookings, setBookings] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const fetchBookings = () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    setLoading(true);
    fetch('http://127.0.0.1:8000/api/booking-history/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then(response => {
        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            navigate('/login');
            throw new Error('Unauthorized. Please log in again.');
          }
          return response.json().then(err => { throw new Error(err.error || 'Failed to fetch bookings'); });
        }
        return response.json();
      })
      .then(data => {
        setBookings(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchBookings();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const handleDownloadPDF = (bookingId) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    setLoading(true);
    fetch(`http://127.0.0.1:8000/api/bookings/${bookingId}/download/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then(response => {
        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            navigate('/login');
            throw new Error('Unauthorized. Please log in again.');
          }
          return response.json().then(err => { throw new Error(err.error || 'Failed to download PDF'); });
        }
        return response.blob();
      })
      .then(blob => {
        const url = window.URL.createObjectURL(new Blob([blob]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `ticket-${bookingId}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  const handleCancelBooking = (bookingId) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    setLoading(true);
    fetch(`http://127.0.0.1:8000/api/bookings/${bookingId}/cancel/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then(response => {
        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            navigate('/login');
            throw new Error('Unauthorized. Please log in again.');
          }
          return response.json().then(err => { throw new Error(err.error || 'Failed to cancel booking'); });
        }
        return response.json();
      })
      .then(data => {
        setLoading(false);
        setError(null);
        fetchBookings(); // Refresh the booking list
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  return (
    <div className="booking-history-container">
      {/* Header */}
      <header className="booking-history-header">
        <div className="container mx-auto px-4">
          <h1>LiveTix</h1>
          <div className="space-x-4">
            <button onClick={() => navigate('/')}>Home</button>
            <button onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="booking-history-main container mx-auto px-4">
        <h2>Your Booking History</h2>

        {loading && (
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-primary"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6 rounded">
            {error}
          </div>
        )}

        {!loading && bookings.length === 0 && !error && (
          <div className="text-center text-gray-600 p-4">
            You have no bookings yet.
          </div>
        )}

        {/* Bookings List */}
        <div className="space-y-4">
          {bookings.map(booking => (
            <div key={booking.id} className="booking-history-card">
              <h3>{booking.concert.title}</h3>
              <p><span>Artist:</span> {booking.concert.artist}</p>
              <p><span>Date:</span> {new Date(booking.concert.date).toLocaleString()}</p>
              <p><span>Venue:</span> {booking.concert.venue}</p>
              <p><span>Booked At:</span> {new Date(booking.booked_at).toLocaleString()}</p>
              <div className="button-group">
                <button
                  onClick={() => handleDownloadPDF(booking.id)}
                  className="download-button"
                  disabled={loading}
                >
                  {loading ? 'Downloading...' : 'Download PDF'}
                </button>
                <button
                  onClick={() => handleCancelBooking(booking.id)}
                  className="cancel-button"
                  disabled={loading}
                >
                  {loading ? 'Canceling...' : 'Cancel Booking'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="booking-history-footer">
        <div className="container mx-auto px-4">
          <p>© 2025 LiveTix. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default BookingHistory;