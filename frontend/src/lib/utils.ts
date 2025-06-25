// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { ApiError } from "aws-amplify/api";

export const getErrorMessage = (error: unknown): string => {
  let message: string;

  if (error instanceof ApiError) {
    if (error.response) {
      const { statusCode, body } = error.response;
      message = `Received ${statusCode} error response with payload: ${body}`;
    } else {
      message =
        "An error ocurred, but there was no response received from the server";
    }
  } else if (error instanceof Error) {
    message = error.message;
  } else if (error && typeof error === "object" && "message" in error) {
    message = String(error.message);
  } else if (typeof error === "string") {
    message = error;
  } else {
    message = "Unknown error";
  }

  return message;
};
