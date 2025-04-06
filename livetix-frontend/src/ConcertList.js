import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ConcertList.css';

function ConcertList() {
  const [concerts, setConcerts] = useState([]);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [showForm, setShowForm] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    setLoading(true);
    fetch('http://127.0.0.1:8000/api/concerts/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then(response => {
        if (!response.ok) {
          if (response.status === 401) {
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              return fetch('http://127.0.0.1:8000/api/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken }),
              })
                .then(refreshResponse => {
                  if (!refreshResponse.ok) {
                    throw new Error('Token refresh failed');
                  }
                  return refreshResponse.json();
                })
                .then(data => {
                  localStorage.setItem('access_token', data.access);
                  return fetch('http://127.0.0.1:8000/api/concerts/', {
                    headers: {
                      'Authorization': `Bearer ${data.access}`,
                      'Content-Type': 'application/json',
                    },
                  });
                })
                .then(newResponse => newResponse.json());
            } else {
              throw new Error('Unauthorized');
            }
          }
          return response.text().then(text => {
            throw new Error(`HTTP error! Status: ${response.status}, Body: ${text}`);
          });
        }
        return response.json();
      })
      .then(data => {
        setConcerts(data);
        setLoading(false);
      })
      .catch(err => {
        if (err.message === 'Unauthorized' || err.message === 'Token refresh failed') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/login');
        } else {
          setError('Failed to fetch concerts: ' + err.message);
        }
        setLoading(false);
      });
  }, [navigate]);

  const handleBook = (id) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }

    setError(null);
    setLoading(true);
    fetch(`http://127.0.0.1:8000/api/concerts/${id}/book/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name: formData.name, email: formData.email }),
    })
      .then(response => {
        if (!response.ok) {
          if (response.status === 401) {
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              return fetch('http://127.0.0.1:8000/api/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken }),
              })
                .then(refreshResponse => {
                  if (!refreshResponse.ok) {
                    throw new Error('Token refresh failed');
                  }
                  return refreshResponse.json();
                })
                .then(data => {
                  localStorage.setItem('access_token', data.access);
                  return fetch(`http://127.0.0.1:8000/api/concerts/${id}/book/`, {
                    method: 'POST',
                    headers: {
                      'Authorization': `Bearer ${data.access}`,
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: formData.name, email: formData.email }),
                  });
                });
            } else {
              throw new Error('Unauthorized');
            }
          }
          return response.json().then(err => { throw new Error(err.error || 'Unknown error'); });
        }
        return response.blob();
      })
      .then(blob => {
        const url = window.URL.createObjectURL(new Blob([blob]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `ticket-${id}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        fetch('http://127.0.0.1:8000/api/concerts/', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        })
          .then(response => response.json())
          .then(data => setConcerts(data));
        setShowForm(null);
        setFormData({ name: '', email: '' });
        setLoading(false);
      })
      .catch(err => {
        if (err.message === 'Unauthorized' || err.message === 'Token refresh failed') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/login');
        } else {
          setError('Booking failed: ' + err.message);
        }
        setLoading(false);
      });
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  return (
    <div>
      {/* Header */}
      <header className="header">
        <h1>LiveTix</h1>
        <div className="nav-buttons">
          <button onClick={() => navigate('/booking-history')}>
            Booking History
          </button>
          <button onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        <h2>Available Concerts</h2>

        {loading && (
          <div className="loading-spinner">
            <div></div>
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {!loading && concerts.length === 0 && !error && (
          <div className="no-concerts">
            No concerts available.
          </div>
        )}

        {/* Concert Grid */}
        <div className="concert-grid">
          {concerts.map(concert => (
            <div key={concert.id} className="concert-card">
              <h3>{concert.title}</h3>
              <div className="details">
                <p><span>Artist:</span> {concert.artist}</p>
                <p><span>Date:</span> {new Date(concert.date).toLocaleString()}</p>
                <p><span>Venue:</span> {concert.venue}</p>
                <p><span>Price:</span> ${concert.ticket_price}</p>
                <p><span>Tickets Available:</span> {concert.available_tickets}</p>
              </div>

              {concert.available_tickets > 0 ? (
                <>
                  {showForm === concert.id ? (
                    <div className="booking-form">
                      <input
                        type="text"
                        placeholder="Your Name"
                        value={formData.name}
                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                        required
                      />
                      <input
                        type="email"
                        placeholder="Your Email"
                        value={formData.email}
                        onChange={e => setFormData({ ...formData, email: e.target.value })}
                        required
                      />
                      <div className="button-group">
                        <button
                          onClick={() => handleBook(concert.id)}
                          className="confirm-button"
                          disabled={loading}
                        >
                          {loading ? 'Booking...' : 'Confirm Booking'}
                        </button>
                        <button
                          onClick={() => setShowForm(null)}
                          className="cancel-button"
                          disabled={loading}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowForm(concert.id)}
                      className="book-button"
                    >
                      Book Ticket
                    </button>
                  )}
                </>
              ) : (
                <p className="sold-out">Sold Out</p>
              )}
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>© 2025 LiveTix. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default ConcertList;