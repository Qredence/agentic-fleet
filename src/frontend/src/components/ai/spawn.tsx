/**
 * Spawn Directive Component
 * Displays dynamic agent creation events in the chat interface
 */

import { Badge } from "@/components/ui/shadcn/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/shadcn/card";
import { Sparkles } from "lucide-react";

interface SpawnSpec {
  role: string;
  capabilities: string[];
  model?: string;
  temperature?: number;
}

interface SpawnProps {
  agentName: string;
  instruction: string;
  spawnSpec: SpawnSpec;
}

export function Spawn({ agentName, instruction, spawnSpec }: SpawnProps) {
  return (
    <Card className="border-l-4 border-l-purple-500 bg-purple-50/50 dark:bg-purple-950/20">
      <CardHeader className="flex flex-row items-center gap-3 pb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900">
          <Sparkles className="h-4 w-4 text-purple-600 dark:text-purple-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-purple-900 dark:text-purple-100">
              Agent Spawned
            </span>
            <Badge variant="secondary" className="text-xs">
              {agentName}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{instruction}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs font-medium text-muted-foreground">
            Role:
          </span>
          <Badge variant="outline" className="text-xs">
            {spawnSpec.role}
          </Badge>
        </div>
        {spawnSpec.capabilities && spawnSpec.capabilities.length > 0 && (
          <div className="flex flex-wrap gap-2 items-start">
            <span className="text-xs font-medium text-muted-foreground">
              Capabilities:
            </span>
            <div className="flex flex-wrap gap-1">
              {spawnSpec.capabilities.map((capability, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs">
                  {capability}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {spawnSpec.model && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">
              Model:
            </span>
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
              {spawnSpec.model}
            </code>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
