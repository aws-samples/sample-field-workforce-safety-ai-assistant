// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { Outlet } from "react-router-dom";
import NavBar from "@/components/NavBar";

export default function Root() {
  return (
    <div className="flex h-[100vh] w-full flex-col">
      <NavBar />
      <Outlet />
    </div>
  );
}
