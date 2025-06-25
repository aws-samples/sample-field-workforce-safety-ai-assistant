import { useNavigate, Routes, Route } from 'react-router-dom';
import { withAuthenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import WorkOrderDetails from '@components/WorkOrderDetails';
import { useEffect, useState } from 'react';
import { WorkOrder, postWorkOrderQuery } from '@lib/api';
import "@cloudscape-design/global-styles/index.css";
import {
  Table,
  Header,
  SpaceBetween,
  StatusIndicator
} from "@cloudscape-design/components";
// Custom StatusBadge component
const StatusBadge = ({ status }: { status: string }) => {
  return <span><StatusIndicator
  type={
    status === "Approved"
      ? "success"
      : status === "In Progress"
      ? "info"
      : status === "Pending"
      ? "warning"
      : "error"
  }
  />
  {status}</span>;
};
const WorkOrderList = () => {
  const navigate = useNavigate();
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 2000; // 2 seconds
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
    const fetchWorkOrders = async (attempt: number = 1) => {
      try {
        setLoading(true);
        const data = await postWorkOrderQuery();
        setWorkOrders(data);
        setError(null);
      } catch (err) {
        console.error(`Attempt ${attempt} failed:`, err);
        if (attempt < MAX_RETRIES) {
          await delay(RETRY_DELAY);
          return fetchWorkOrders(attempt + 1);
        } else {
          setError(`Failed to load work orders. Please try again later.`);
        }
      } finally {
          setLoading(false);
      }
    };
    fetchWorkOrders();
    // Cleanup function to handle component unmount
    return () => {
      setLoading(false);
      setError(null);
    };
  }, []);
  if (loading) {
    return <div>
      Loading...
    </div>;
  }
  if (error) {
    return <div>{error}</div>;
  }
  return (
    <SpaceBetween size="l">
      <Table
        header={
          <Header>
            Work Order Queue
          </Header>
        }
        columnDefinitions={[
          { header: "ID", cell: (item) => item.work_order_id },
          { header: "Description", cell: (item) => item.description },
          { header: "Location", cell: (item) => item.location_name },
          { header: "Asset", cell: (item) => item.asset_id },
          { header: "Status", cell: (item) => <StatusBadge status={item.status} />},
          {
            header: "Scheduled Date",
            cell: (item) =>
              new Date(item.scheduled_start_timestamp).toLocaleString(),
          },
        ]}
        items={workOrders}
        onRowClick={({ detail }) =>
          navigate(`/workorder/${detail.item.work_order_id}`, {
            state: { workOrder: detail.item },
          })
        }
      />
    </SpaceBetween>
  );
};
function App() {
  return (
    <Routes>
      <Route path="/" element={<WorkOrderList />} />
      <Route path="/workorder/:id" element={<WorkOrderDetails />} />
    </Routes>
  );
}
export default withAuthenticator(App);
