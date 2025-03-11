import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://internal-3-Tier-AppTier-LoadBalancer-1067329975.us-east-1.elb.amazonaws.com/api';
console.log('API URL being used:', API_URL); // Log the API URL on initial load


function App() {
  const [todos, setTodos] = useState([]);
  const [newTodo, setNewTodo] = useState('');
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('checking'); // Add this line

  useEffect(() => {
    // Add health check function
    const checkConnection = async () => {
      try {
        console.log('Attempting to connect to API...');
        const response = await fetch(`${API_URL}/health`);
        const data = await response.text();
        console.log('Health check response:', data);
        setConnectionStatus('connected');
      } catch (error) {
        console.error('Health check failed:', error);
        setConnectionStatus('failed');
      }
    };

    // Modified fetchTodos with better logging
    const fetchTodos = async () => {
      try {
        console.log('Fetching todos from:', `${API_URL}/todos`);
        const response = await fetch(`${API_URL}/todos`);
        console.log('Todos response status:', response.status);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Received todos:', data);
        setTodos(Array.isArray(data) ? data : []);
        setError(null);
      } catch (error) {
        console.error('Detailed error fetching todos:', {
          message: error.message,
          stack: error.stack,
          url: `${API_URL}/todos`
        });
        setError('Failed to fetch todos. Please try again later.');
        setTodos([]);
      }
    };

    // Execute both checks
    checkConnection();
    fetchTodos();
  }, []);



  const addTodo = async () => {
    if (newTodo.trim() === '') return;
    try {
      const response = await fetch(`${API_URL}/todos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: newTodo }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTodos(prevTodos => [...prevTodos, data]);
      setNewTodo('');
      setError(null);
    } catch (error) {
      console.error('Error adding todo:', error);
      setError('Failed to add todo. Please try again later.');
    }
  };

  const deleteTodo = async (id) => {
    try {
      const response = await fetch(`${API_URL}/todos/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setTodos(prevTodos => prevTodos.filter(todo => todo.id !== id));
      setError(null);
    } catch (error) {
      console.error('Error deleting todo:', error);
      setError('Failed to delete todo. Please try again later.');
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMessage('File uploaded successfully: ' + response.data.file_url);
    } catch (error) {
      setMessage('Error uploading file: ' + error.message);
    }
  };

  return (
    <div className="App">
      <h1>Todo App</h1>
      <div style={{
        padding: '10px',
        backgroundColor: connectionStatus === 'connected' ? '#dff0d8' : '#f2dede',
        marginBottom: '10px'
      }}>
        API Status: {connectionStatus}
      </div>
      {error && <p style={{color: 'red'}}>{error}</p>}
      <div>
        <input
          type="text"
          value={newTodo}
          onChange={(e) => setNewTodo(e.target.value)}
          placeholder="Enter a new todo"
        />
        <button onClick={addTodo}>Add Todo</button>
      </div>
      <ul>
        {todos.map((todo) => (
          <li key={todo.id}>
            {todo.task}
            <button onClick={() => deleteTodo(todo.id)}>Delete</button>
          </li>
        ))}
      </ul>
      <header className="App-header">
        <h1>File Upload</h1>
        <form onSubmit={handleSubmit}>
          <input type="file" onChange={handleFileChange} />
          <button type="submit">Upload</button>
        </form>
        {message && <p>{message}</p>}
      </header>
    </div>
  );
}

export default App;