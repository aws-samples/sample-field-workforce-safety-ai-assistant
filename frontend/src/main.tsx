import * as React from "react";
import * as ReactDOM from "react-dom/client";
import { Authenticator } from "@aws-amplify/ui-react";
import {
  createBrowserRouter,
  RouterProvider,
  createRoutesFromElements,
  Route,
} from "react-router-dom";

import "./index.css";
import "@/lib/api";
import App from './App';
import Root from "@/routes/Root";
import Error from "@/routes/Error";
import WorkOrderDetails from './components/WorkOrderDetails';

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route path="/*" element={<Root />} errorElement={<Error />}>
      <Route index element={<App />} />
      <Route path="workorder/:id" element={<WorkOrderDetails />} />
    </Route>,
  ),
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Authenticator hideSignUp={false}>
      <RouterProvider router={router} />
    </Authenticator>
  </React.StrictMode>,
);
