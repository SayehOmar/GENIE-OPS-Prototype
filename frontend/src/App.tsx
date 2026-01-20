import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import SaaSList from './pages/SaaSList';
import SaaSForm from './pages/SaaSForm';
import Submissions from './pages/Submissions';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/saas" element={<SaaSList />} />
          <Route path="/saas/new" element={<SaaSForm />} />
          <Route path="/saas/:id/edit" element={<SaaSForm />} />
          <Route path="/submissions" element={<Submissions />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
