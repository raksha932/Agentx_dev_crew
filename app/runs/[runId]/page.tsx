'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Shield, Loader2, GitBranch, AlertTriangle, Wrench, GitPullRequest, CheckCircle, XCircle, Activity, FileCode, ExternalLink, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '@/hooks/use-toast';
import { getRunDetails, WebSocketMessage, RunDetail, Issue, Fix } from '@/lib/api';

const AGENT_ORDER = [
  { id: 'orchestrator', name: 'Orchestrator' },
  { id: 'repository_intelligence', name: 'Repo Intel' },
  { id: 'code_analysis', name: 'Code Analysis' },
  { id: 'security_scanner', name: 'Security' },
  { id: 'root_cause_analysis', name: 'Root Cause' },
  { id: 'fix_generator', name: 'Fix Gen' },
  { id: 'validation_agent', name: 'Validation' },
  { id: 'verification_agent', name: 'Verification' },
  { id: 'pr_creation', name: 'PR Creation' },
];

const severityColors: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-amber-500',
  low: 'bg-blue-500',
};

interface AgentState {
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
}

export default function RunDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.runId as string;
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runData, setRunData] = useState<RunDetail | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>({});
  const [logs, setLogs] = useState<{ timestamp: string; agent: string; message: string; type: 'info' | 'success' | 'error' }[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

  // Fetch run details from REAL API
  const fetchRunDetails = useCallback(async () => {
    try {
      // REAL API CALL: GET /api/v1/runs/{runId}
      const response = await fetch(`${API_URL}/runs/${runId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Run not found. The run may have been deleted or the ID is invalid.');
        }
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      const data: RunDetail = await response.json();
      setRunData(data);
      setError(null);

      // Update agent states from REAL data
      if (data.agent_executions) {
        const states: Record<string, AgentState> = {};
        AGENT_ORDER.forEach(agent => {
          const exec = data.agent_executions.find(e => e.agent_name === agent.id);
          states[agent.id] = {
            status: exec?.status as any || 'pending',
            progress: exec?.progress || 0,
          };
        });
        setAgentStates(states);
      }

    } catch (err: any) {
      setError(err.message || 'Failed to fetch run details');
    } finally {
      setIsLoading(false);
    }
  }, [runId, API_URL]);

  // Initial fetch
  useEffect(() => {
    fetchRunDetails();
  }, [fetchRunDetails]);

  // WebSocket connection for REAL-TIME updates
  useEffect(() => {
    if (!runId) return;

    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket(`${WS_URL}/ws/runs/${runId}`);

        wsRef.current.onopen = () => {
          setWsConnected(true);
          console.log('WebSocket connected to run:', runId);
        };

        wsRef.current.onmessage = (event) => {
          try {
            const msg: WebSocketMessage = JSON.parse(event.data);

            // Ignore ping/pong
            if (msg.status === 'ping' || msg.status === 'pong') return;

            // Add log entry
            setLogs(prev => [...prev, {
              timestamp: msg.timestamp,
              agent: msg.agent,
              message: msg.message,
              type: msg.status === 'failed' ? 'error' : msg.status === 'completed' ? 'success' : 'info',
            }]);

            // Update agent state
            if (msg.agent) {
              const agentKey = msg.agent.toLowerCase().replace(/ /g, '_');
              setAgentStates(prev => ({
                ...prev,
                [agentKey]: {
                  status: msg.status as any,
                  progress: msg.progress,
                },
              }));
            }

            // Handle completion with data
            if (msg.data) {
              if (msg.data.issues) {
                setRunData(prev => prev ? { ...prev, issues: msg.data.issues as Issue[] } : null);
              }
              if (msg.data.fixes) {
                setRunData(prev => prev ? { ...prev, fixes: msg.data.fixes as Fix[] } : null);
              }
              if (msg.data.pr_url) {
                setRunData(prev => prev ? {
                  ...prev,
                  pull_request: {
                    id: '1',
                    pr_url: msg.data.pr_url as string,
                    github_pr_number: null,
                    status: 'created',
                    title: null,
                  },
                } : null);
              }
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        wsRef.current.onclose = () => {
          setWsConnected(false);
          console.log('WebSocket disconnected');
          // Attempt reconnection after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };

        wsRef.current.onerror = (e) => {
          console.error('WebSocket error:', e);
        };
      } catch (e) {
        console.error('Failed to create WebSocket:', e);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [runId, WS_URL]);

  // Polling as fallback when WebSocket is disconnected
  useEffect(() => {
    if (wsConnected || runData?.status === 'completed') return;

    pollingRef.current = setInterval(fetchRunDetails, 3000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [wsConnected, runData?.status, fetchRunDetails]);

  const overallProgress = AGENT_ORDER.reduce((sum, agent) => {
    const state = agentStates[agent.id];
    return sum + (state?.progress || 0);
  }, 0) / AGENT_ORDER.length;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading run details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Card className="bg-slate-900/50 border-slate-800 max-w-md">
          <CardContent className="py-8 text-center">
            <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Error Loading Run</h2>
            <p className="text-slate-400 mb-4">{error}</p>
            <Button onClick={() => router.push('/dashboard')} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950">
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const issues = runData?.issues || [];
  const fixes = runData?.fixes || [];
  const pullRequest = runData?.pull_request;
  const runStatus = runData?.status || 'queued';
  const repoUrl = runData?.repo_url || '';
  const branch = runData?.branch || 'main';

  const getRepoName = (url: string) => {
    const parts = url.split('/');
    return parts.slice(-2).join('/');
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 backdrop-blur-sm sticky top-0 z-50 bg-slate-950/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
            <Shield className="h-8 w-8 text-emerald-400" />
            <span className="text-xl font-bold tracking-tight">CodeSentinel</span>
          </div>
          <nav className="flex items-center gap-6">
            <span className={`text-sm ${wsConnected ? 'text-emerald-400' : 'text-slate-400'} flex items-center gap-1`}>
              <Activity className={`h-4 w-4 ${wsConnected ? '' : 'animate-pulse'}`} />
              {wsConnected ? 'Live' : 'Polling'}
            </span>
            <a href="/dashboard" className="text-slate-400 hover:text-white">Dashboard</a>
            <a href="/runs" className="text-slate-400 hover:text-white">Runs</a>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Run Header */}
        <div className="mb-8 flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <GitBranch className="h-6 w-6 text-emerald-400" />
              <h1 className="text-2xl font-bold">{getRepoName(repoUrl) || `Run ${runId}`}</h1>
              <Badge className={`${
                runStatus === 'completed' ? 'bg-emerald-500' :
                runStatus === 'running' ? 'bg-blue-500' :
                runStatus === 'failed' ? 'bg-red-500' : 'bg-slate-500'
              } text-white capitalize`}>
                {runStatus}
              </Badge>
            </div>
            <p className="text-slate-400">
              Branch: {branch} • Run ID: {runId}
            </p>
          </div>
          <Button variant="outline" onClick={fetchRunDetails}>
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>
        </div>

        {/* Progress */}
        <Card className="bg-slate-900/50 border-slate-800 mb-8">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-400" />
              Pipeline Progress
              <span className="text-sm font-normal text-slate-400 ml-auto">
                {Math.round(overallProgress)}% Complete
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="w-full h-3 bg-slate-800 rounded-full mb-6 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
                animate={{ width: `${overallProgress}%` }}
              />
            </div>

            <div className="grid grid-cols-3 md:grid-cols-9 gap-3">
              {AGENT_ORDER.map((agent) => {
                const state = agentStates[agent.id];
                return (
                  <div key={agent.id} className="text-center">
                    <div className={`w-full aspect-square rounded-xl flex items-center justify-center mb-2 border-2 transition-all ${
                      state?.status === 'completed' ? 'bg-emerald-500/20 border-emerald-500' :
                      state?.status === 'running' ? 'bg-blue-500/20 border-blue-500' :
                      state?.status === 'failed' ? 'bg-red-500/20 border-red-500' : 'bg-slate-800/50 border-slate-700'
                    }`}>
                      {state?.status === 'completed' ? (
                        <CheckCircle className="h-5 w-5 text-emerald-400" />
                      ) : state?.status === 'running' ? (
                        <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
                      ) : state?.status === 'failed' ? (
                        <XCircle className="h-5 w-5 text-red-400" />
                      ) : (
                        <span className="text-slate-500 text-xs">{AGENT_ORDER.indexOf(agent) + 1}</span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400">{agent.name}</div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="logs" className="space-y-4">
          <TabsList className="bg-slate-900/50 border border-slate-800">
            <TabsTrigger value="logs" className="data-[state=active]:bg-emerald-500/20">
              <Activity className="mr-2 h-4 w-4" /> Live Logs ({logs.length})
            </TabsTrigger>
            <TabsTrigger value="issues" className="data-[state=active]:bg-emerald-500/20">
              <AlertTriangle className="mr-2 h-4 w-4" /> Issues ({issues.length})
            </TabsTrigger>
            <TabsTrigger value="fixes" className="data-[state=active]:bg-emerald-500/20">
              <Wrench className="mr-2 h-4 w-4" /> Fixes ({fixes.length})
            </TabsTrigger>
            {pullRequest?.pr_url && (
              <TabsTrigger value="pr" className="data-[state=active]:bg-emerald-500/20">
                <GitPullRequest className="mr-2 h-4 w-4" /> PR
              </TabsTrigger>
            )}
          </TabsList>

          {/* Logs Tab */}
          <TabsContent value="logs">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-lg">Pipeline Logs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 overflow-y-auto bg-slate-950/50 rounded-lg p-4 font-mono text-sm">
                  {logs.length === 0 ? (
                    <p className="text-slate-500">
                      {runStatus === 'running' ? 'Waiting for logs from backend...' : 'No logs available'}
                    </p>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className={`flex gap-3 py-1 ${
                        log.type === 'success' ? 'text-emerald-400' :
                        log.type === 'error' ? 'text-red-400' : 'text-slate-300'
                      }`}>
                        <span className="text-slate-500 w-24">{new Date(log.timestamp).toLocaleTimeString()}</span>
                        <span className="text-blue-400 w-32">[{log.agent}]</span>
                        <span>{log.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Issues Tab */}
          <TabsContent value="issues" className="space-y-4">
            {issues.length === 0 ? (
              <Card className="bg-slate-900/50 border-slate-800">
                <CardContent className="py-12 text-center">
                  {runStatus === 'completed' ? (
                    <>
                      <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
                      <p className="text-slate-400">No issues found</p>
                    </>
                  ) : (
                    <>
                      <Loader2 className="h-12 w-12 text-blue-400 mx-auto mb-4 animate-spin" />
                      <p className="text-slate-400">Analyzing code for issues...</p>
                    </>
                  )}
                </CardContent>
              </Card>
            ) : (
              issues.map((issue) => (
                <Card key={issue.id} className="bg-slate-900/50 border-slate-800">
                  <CardContent className="py-4">
                    <div className="flex items-start gap-4">
                      <Badge className={`${severityColors[issue.severity] || 'bg-slate-500'} text-white capitalize flex-shrink-0`}>
                        {issue.severity}
                      </Badge>
                      <div className="flex-1">
                        <div className="font-medium mb-1">{issue.title}</div>
                        {issue.description && <p className="text-sm text-slate-400 mb-2">{issue.description}</p>}
                        {issue.file_path && (
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <FileCode className="h-4 w-4" />
                            <span>{issue.file_path}{issue.line_number ? `:${issue.line_number}` : ''}</span>
                          </div>
                        )}
                        {issue.code_snippet && (
                          <pre className="mt-2 p-3 rounded bg-slate-800/50 text-sm font-mono overflow-x-auto">
                            <code>{issue.code_snippet}</code>
                          </pre>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          {/* Fixes Tab */}
          <TabsContent value="fixes" className="space-y-4">
            {fixes.length === 0 ? (
              <Card className="bg-slate-900/50 border-slate-800">
                <CardContent className="py-12 text-center">
                  <Wrench className="h-12 w-12 text-slate-500 mx-auto mb-4" />
                  <p className="text-slate-400">
                    {issues.length > 0 ? 'Generating fixes...' : 'No fixes generated'}
                  </p>
                </CardContent>
              </Card>
            ) : (
              fixes.map((fix) => (
                <Card key={fix.id} className="bg-slate-900/50 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-base">{fix.issue_title}</CardTitle>
                    {fix.explanation && <CardDescription>{fix.explanation}</CardDescription>}
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2 mb-3">
                      <Badge variant="secondary">Confidence: {Math.round(fix.confidence * 100)}%</Badge>
                      <Badge variant="outline" className="capitalize">{fix.status}</Badge>
                    </div>
                    <pre className="p-3 rounded bg-slate-800/50 text-sm font-mono overflow-x-auto">
                      <code>{fix.patch}</code>
                    </pre>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          {/* PR Tab */}
          {pullRequest?.pr_url && (
            <TabsContent value="pr">
              <Card className="bg-slate-900/50 border-slate-800 border-emerald-500/50">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <GitPullRequest className="h-5 w-5 text-emerald-400" />
                    Pull Request Created
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">URL:</span>
                      <a href={pullRequest.pr_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1">
                        {pullRequest.pr_url}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    <Button onClick={() => window.open(pullRequest.pr_url!, '_blank')} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950">
                      <GitPullRequest className="mr-2 h-4 w-4" /> View Pull Request
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </main>
    </div>
  );
}
