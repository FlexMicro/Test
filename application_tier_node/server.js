// const express = require('express');
// const cors = require('cors');
// const dotenv = require('dotenv');
// const todoRoutes = require('./routes/todos');
// const errorHandler = require('./middlewares/errorHandler');

// dotenv.config();

// const app = express();
// const PORT = process.env.PORT || 3000;

// app.use(cors());
// app.use(express.json());

// app.use('/api/todos', todoRoutes);

// app.use(errorHandler);

// app.listen(PORT, () => {
//   console.log(`Server running on port ${PORT}`);
// });

const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const db = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});

db.connect((err) => {
  if (err) {
    console.error('Error connecting to the database:', err);
    return;
  }
  console.log('Connected to the database');
});

app.get('/api/todos', (req, res) => {
  db.query('SELECT * FROM todos', (err, results) => {
    if (err) {
      res.status(500).json({ error: 'Error fetching todos' });
      return;
    }
    res.json(results);
  });
});

app.post('/api/todos', (req, res) => {
  const { task } = req.body;
  db.query('INSERT INTO todos (task) VALUES (?)', [task], (err, result) => {
    if (err) {
      res.status(500).json({ error: 'Error adding todo' });
      return;
    }
    res.json({ id: result.insertId, task });
  });
});

app.delete('/api/todos/:id', (req, res) => {
  const { id } = req.params;
  db.query('DELETE FROM todos WHERE id = ?', [id], (err) => {
    if (err) {
      res.status(500).json({ error: 'Error deleting todo' });
      return;
    }
    res.json({ message: 'Todo deleted successfully' });
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});