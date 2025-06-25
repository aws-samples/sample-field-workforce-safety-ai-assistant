// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/
import { getErrorMessage } from "@/lib/utils";
import { useRouteError } from "react-router-dom";
export default function Error() {
  const error = useRouteError();
  return (
    <main id="error-page">
      <h3>Oops!</h3>
      <p>Sorry, an unexpected error has occurred.</p>
      <code>
        <i>{getErrorMessage(error)}</i>
      </code>
      <footer>Industrial AI Demo</footer>
    </main>
  );
}
