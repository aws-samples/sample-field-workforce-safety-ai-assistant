// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

export type QueryObject = {
  query: string;
  session_id: string;
};

export type EmergencyCheckQuery = {
  latitude: number;
  longitude: number;
};

export type RatingObject = {
  session_id: string;
  question: string;
  answer: string;
  author: string;
  timestamp: number;
  rating: string;
};

export interface DataResponse {
  question: string;
  answers: string;
  sources: string[]; // or appropriate type for your sources
}

export interface Message {
  id: string;
  author: string;
  message_type: string;
  question?: string;
  content: string;
  sources?: string[];
  timestamp?: number;
  rating?: string;
  session_id?: string;
}
