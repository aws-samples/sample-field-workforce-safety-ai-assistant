// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { IconMessageChatbot, IconUser } from "@tabler/icons-react";
import { useAuthenticator } from "@aws-amplify/ui-react";

interface UserAvatarProps {
  userType: "user" | "bot";
  size?: "default" | "small";
}

export default function UserAvatar({
  userType,
  size = "default",
}: UserAvatarProps) {
  const { user } = useAuthenticator((context) => [context.user]);

  const sizeVariants: { [key: string]: string } = {
    default: "h-10 w-10 leading-10 text-lg",
    small: "h-8 w-8 leading-8 text-sm",
  };

  const sizeClasses = sizeVariants[size] || sizeVariants.default;

  return (
    <div
      className={`${sizeClasses} flex flex-none select-none rounded-full
        ${
          userType && userType === "bot"
            ? "mr-2 bg-pink-600 dark:bg-pink-500"
            : "ml-2 bg-orange-500 text-orange-200 dark:bg-orange-400 dark:text-orange-950"
        }`}
    >
      {userType === "user" && (
        <span className="flex-1 text-center font-semibold">
          {user.username.charAt(0).toUpperCase()}
        </span>
      )}

      {userType === "bot" && (
        <IconMessageChatbot className="m-auto stroke-pink-200" />
      )}

      {!userType && <IconUser size={20} className="m-auto stroke-orange-200" />}
    </div>
  );
}
