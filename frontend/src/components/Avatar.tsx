// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { IconMessageChatbot, IconUser } from "@tabler/icons-react";
import { useAuthenticator } from "@aws-amplify/ui-react";

type AvatarProps = {
  avatarType: "user" | "bot";
  size?: "default" | "small";
};

const Avatar: React.FC<AvatarProps> = ({ avatarType, size = "default" }) => {
  const {
    user: { username },
  } = useAuthenticator((context) => [context.user]);

  const sizeVariants: { [key: string]: string } = {
    default: "h-10 w-10 leading-10 text-lg",
    small: "h-8 w-8 leading-8 text-sm",
  };

  const sizeClasses = sizeVariants[size] || sizeVariants.default;

  return (
    <div
      className={`${sizeClasses} flex flex-none select-none rounded-full
        ${
          avatarType && avatarType === "bot"
            ? "mr-2 bg-pink-600 dark:bg-pink-500"
            : "ml-2 bg-orange-500 text-orange-200 dark:bg-orange-400 dark:text-orange-950"
        }`}
    >
      {avatarType === "user" && (
        <span className="flex-1 text-center font-semibold">
          {username.charAt(0).toUpperCase()}
        </span>
      )}

      {avatarType === "bot" && (
        <IconMessageChatbot className="m-auto stroke-pink-200" />
      )}

      {!avatarType && (
        <IconUser size={20} className="m-auto stroke-orange-200" />
      )}
    </div>
  );
};

export default Avatar;
