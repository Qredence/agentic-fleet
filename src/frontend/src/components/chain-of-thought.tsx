import React from "react";

import {
  Task,
  TaskItem,
  TaskItemFile,
  TaskTrigger,
  TaskContent,
} from "@/components/ai-elements/task";

import {
  SiReact,
  SiTypescript,
  SiJavascript,
  SiCss,
  SiHtml5,
  SiJson,
  SiMarkdown,
} from "@icons-pack/react-simple-icons";
import type { Thought, ThoughtItem } from "../api/types";

const iconMap = {
  react: { component: SiReact, color: "#149ECA" },
  typescript: { component: SiTypescript, color: "#3178C6" },
  javascript: { component: SiJavascript, color: "#F7DF1E" },
  css: { component: SiCss, color: "#1572B6" },
  html: { component: SiHtml5, color: "#E34F26" },
  json: { component: SiJson, color: "#000000" },
  markdown: { component: SiMarkdown, color: "#000000" },
};

interface ChainOfThoughtProps {
  thoughts: Thought[];
}

const ChainOfThought: React.FC<ChainOfThoughtProps> = ({ thoughts }) => {
  if (!thoughts || thoughts.length === 0) return null;

  const renderTaskItem = (item: ThoughtItem, index: number) => {
    if (item?.type === "file" && item.file) {
      const iconInfo = iconMap[item.file.icon as keyof typeof iconMap] || {
        component: SiMarkdown,
        color: "#000000",
      };
      const IconComponent = iconInfo.component;
      return (
        <span className="inline-flex items-center gap-1" key={index}>
          {item.text}
          <TaskItemFile>
            <IconComponent
              color={item.file.color || iconInfo.color}
              className="size-4"
            />
            <span>{item.file.name}</span>
          </TaskItemFile>
        </span>
      );
    }
    return item?.text || "";
  };

  return (
    <div className="max-w-3xl mx-auto mb-8">
      {thoughts.map((thought, idx) => (
        <Task
          key={idx}
          defaultOpen={idx === thoughts.length - 1}
          status={thought.status}
        >
          <TaskTrigger
            title={thought.title}
            description={thought.description}
          />
          <TaskContent>
            {thought.items?.map((item, itemIndex) => (
              <TaskItem key={itemIndex}>
                {renderTaskItem(item, itemIndex)}
              </TaskItem>
            ))}
          </TaskContent>
        </Task>
      ))}
    </div>
  );
};

export default ChainOfThought;
