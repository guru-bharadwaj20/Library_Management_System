import React, { useState, useEffect } from 'react';
import Papa from 'papaparse';
import './App.css';

const App = () => {
  const [books, setBooks] = useState([]);
  const [students, setStudents] = useState([]);
  const [filteredBooks, setFilteredBooks] = useState([]);
  const [filteredStudents, setFilteredStudents] = useState([]);
  const [bookSearch, setBookSearch] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [issueBookId, setIssueBookId] = useState('');
  const [issueStudentId, setIssueStudentId] = useState('');
  const [returnBookId, setReturnBookId] = useState('');
  const [returnStudentId, setReturnStudentId] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      Papa.parse('/books.csv', {
        download: true,
        header: false,
        complete: (results) => {
          const booksData = results.data.map(row => ({
            book_id: row[0],
            title: row[1],
            author: row[2],
            available_copies: parseInt(row[3], 10)
          })).filter(book => book.book_id);
          setBooks(booksData);
          setFilteredBooks(booksData);
        }
      });

      Papa.parse('/students.csv', {
        download: true,
        header: false,
        complete: (results) => {
          const studentsData = results.data.map(row => ({
            student_id: row[0],
            name: row[1],
            borrowed_books: row[2] ? row[2].split(',').filter(id => id) : []
          })).filter(student => student.student_id);
          setStudents(studentsData);
          setFilteredStudents(studentsData);
        }
      });
    };
    fetchData();
  }, []);

  useEffect(() => {
    setFilteredBooks(
      books.filter(book =>
        (book.title && book.title.toLowerCase().includes(bookSearch.toLowerCase())) ||
        (book.author && book.author.toLowerCase().includes(bookSearch.toLowerCase()))
      )
    );
  }, [bookSearch, books]);

  useEffect(() => {
    setFilteredStudents(
      students.filter(student =>
        student.name && student.name.toLowerCase().includes(studentSearch.toLowerCase())
      )
    );
  }, [studentSearch, students]);

  const handleIssueBook = () => {
    const book = books.find(b => b.book_id === issueBookId);
    const student = students.find(s => s.student_id === issueStudentId);

    if (!book || !student) {
      alert("Book or Student not found.");
      return;
    }

    if (book.available_copies <= 0) {
      alert("Book is not available.");
      return;
    }

    if (student.borrowed_books.length >= 5) {
      alert("Student has reached the borrowing limit.");
      return;
    }

    const updatedStudents = students.map(s =>
      s.student_id === issueStudentId
        ? { ...s, borrowed_books: [...s.borrowed_books, issueBookId] }
        : s
    );
    setStudents(updatedStudents);

    const updatedBooks = books.map(b =>
      b.book_id === issueBookId
        ? { ...b, available_copies: b.available_copies - 1 }
        : b
    );
    setBooks(updatedBooks);

    alert(`Book '${book.title}' issued to ${student.name}.`);
    setIssueBookId('');
    setIssueStudentId('');
  };

  const handleReturnBook = () => {
    const book = books.find(b => b.book_id === returnBookId);
    const student = students.find(s => s.student_id === returnStudentId);

    if (!book || !student) {
      alert("Book or Student not found.");
      return;
    }

    if (!student.borrowed_books.includes(returnBookId)) {
      alert("This book was not borrowed by the student.");
      return;
    }

    const updatedStudents = students.map(s =>
      s.student_id === returnStudentId
        ? { ...s, borrowed_books: s.borrowed_books.filter(b => b !== returnBookId) }
        : s
    );
    setStudents(updatedStudents);

    const updatedBooks = books.map(b =>
      b.book_id === returnBookId
        ? { ...b, available_copies: b.available_copies + 1 }
        : b
    );
    setBooks(updatedBooks);

    alert(`Book '${book.title}' returned.`);
    setReturnBookId('');
    setReturnStudentId('');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Library Management System</h1>
      </header>
      <div className="container">
        <div className="card">
          <h2>Book Management</h2>
          <div className="form-group">
            <input
              type="text"
              placeholder="Search for books..."
              value={bookSearch}
              onChange={e => setBookSearch(e.target.value)}
            />
          </div>
          <div className="results">
            {filteredBooks.map(book => (
              <div key={book.book_id} className="item-card">
                <p><strong>ID:</strong> {book.book_id}</p>
                <p><strong>Title:</strong> {book.title}</p>
                <p><strong>Author:</strong> {book.author}</p>
                <p><strong>Available:</strong> {book.available_copies}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Student Management</h2>
          <div className="form-group">
            <input
              type="text"
              placeholder="Search for students..."
              value={studentSearch}
              onChange={e => setStudentSearch(e.target.value)}
            />
          </div>
          <div className="results">
            {filteredStudents.map(student => (
              <div key={student.student_id} className="item-card">
                <p><strong>ID:</strong> {student.student_id}</p>
                <p><strong>Name:</strong> {student.name}</p>
                <p><strong>Borrowed:</strong> {student.borrowed_books.join(', ')}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Actions</h2>
          <div className="action-section">
            <h3>Issue Book</h3>
            <div className="form-group">
              <input
                type="text"
                placeholder="Book ID"
                value={issueBookId}
                onChange={e => setIssueBookId(e.target.value)}
              />
              <input
                type="text"
                placeholder="Student ID"
                value={issueStudentId}
                onChange={e => setIssueStudentId(e.target.value)}
              />
              <button onClick={handleIssueBook}>Issue</button>
            </div>
          </div>
          <div className="action-section">
            <h3>Return Book</h3>
            <div className="form-group">
              <input
                type="text"
                placeholder="Book ID"
                value={returnBookId}
                onChange={e => setReturnBookId(e.target.value)}
              />
              <input
                type="text"
                placeholder="Student ID"
                value={returnStudentId}
                onChange={e => setReturnStudentId(e.target.value)}
              />
              <button onClick={handleReturnBook}>Return</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
