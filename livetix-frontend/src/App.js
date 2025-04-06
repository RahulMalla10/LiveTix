import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import ConcertList from './ConcertList';
import Login from './Login';
import Register from './Register';
import BookingHistory from './BookingHistory';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ConcertList />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/booking-history" element={<BookingHistory />} />
      </Routes>
    </Router>
  );
}

export default App;