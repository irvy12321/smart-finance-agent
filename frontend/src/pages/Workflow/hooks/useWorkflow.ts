import { useState, useCallback, useRef, useEffect } from 'react'
import { Node, Edge } from 'reactflow'
import type {
  WorkflowState,
  WorkflowActions,
  WorkflowEvent,
  TaskNodeData,
  TaskStatus,
  DagSubtask,
} from '../types'
import { TOOL_DISPLAY_NAMES } from '../types'

const initialState: WorkflowState = {
  taskId: null,
  traceId: null,
  query: null,
  status: 'idle',
  nodes: [],
  edges: [],
  subtasks: [],
  route: null,
  taskResults: new Map(),
  events: [],
  metrics: {
    totalTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    totalDuration: 0,
    avgTaskDuration: 0,
  },
  selectedTaskId: null,
  selectedTask: null,
}

export function useWorkflow(): [WorkflowState, WorkflowActions] {
  const [state, setState] = useState<WorkflowState>(initialState)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  // Convert subtasks to React Flow nodes and edges
  const buildDAG = useCallback((subtasks: DagSubtask[]): { nodes: Node<TaskNodeData>[], edges: Edge[] } => {
    const nodes: Node<TaskNodeData>[] = []
    const edges: Edge[] = []

    // Add planner node
    nodes.push({
      id: 'planner',
      type: 'plannerNode',
      position: { x: 0, y: 0 },
      data: {
        id: 'planner',
        label: 'Planner',
        tool: 'planner',
        status: 'success',
        duration_ms: 0,
        description: 'Task planning and decomposition',
      },
    })

    // Add task nodes
    subtasks.forEach((subtask) => {
      const isSynthesize = subtask.tool === 'llm_synthesize'

      nodes.push({
        id: subtask.id,
        type: isSynthesize ? 'synthesizerNode' : 'taskNode',
        position: { x: 0, y: 0 },
        data: {
          id: subtask.id,
          label: TOOL_DISPLAY_NAMES[subtask.tool] || subtask.tool,
          tool: subtask.tool,
          status: 'pending',
          duration_ms: 0,
          description: subtask.desc,
          confidence: subtask.confidence,
        },
      })

      // Add edges from planner to first tasks
      if (subtask.depends_on.length === 0) {
        edges.push({
          id: `planner-${subtask.id}`,
          source: 'planner',
          target: subtask.id,
          animated: true,
          style: { stroke: '#6b7280' },
        })
      }

      // Add edges for dependencies
      subtask.depends_on.forEach((depId) => {
        edges.push({
          id: `${depId}-${subtask.id}`,
          source: depId,
          target: subtask.id,
          animated: true,
          style: { stroke: '#6b7280' },
        })
      })
    })

    // Add report node
    nodes.push({
      id: 'report',
      type: 'reportNode',
      position: { x: 0, y: 0 },
      data: {
        id: 'report',
        label: 'Report',
        tool: 'report',
        status: 'pending',
        duration_ms: 0,
        description: 'Final research report',
      },
    })

    // Add edge from last task to report
    const lastTasks = subtasks.filter(s => s.tool === 'llm_synthesize')
    if (lastTasks.length > 0) {
      edges.push({
        id: `${lastTasks[0].id}-report`,
        source: lastTasks[0].id,
        target: 'report',
        animated: true,
        style: { stroke: '#6b7280' },
      })
    }

    return { nodes, edges }
  }, [])

  // Update node status
  const updateNodeStatus = useCallback((taskId: string, status: TaskStatus, duration_ms?: number, data?: string, error?: string) => {
    setState(prev => {
      const newNodes = prev.nodes.map(node => {
        if (node.id === taskId) {
          return {
            ...node,
            data: {
              ...node.data,
              status,
              duration_ms: duration_ms ?? node.data.duration_ms,
              data: data ?? node.data.data,
              error: error ?? node.data.error,
            },
          }
        }
        return node
      })

      // Update edge style based on status
      const newEdges = prev.edges.map(edge => {
        if (edge.target === taskId || edge.source === taskId) {
          const color = status === 'success' ? '#22c55e' :
                       status === 'running' ? '#3b82f6' :
                       status === 'failed' ? '#ef4444' : '#6b7280'
          return { ...edge, style: { ...edge.style, stroke: color } }
        }
        return edge
      })

      return { ...prev, nodes: newNodes, edges: newEdges }
    })
  }, [])

  // Handle SSE event
  const handleEvent = useCallback((event: WorkflowEvent) => {
    setState(prev => {
      const newEvents = [...prev.events, event]
      const newTaskResults = new Map(prev.taskResults)

      const newState: Partial<WorkflowState> = {
        events: newEvents,
        traceId: event.trace_id ?? prev.traceId,
      }

      switch (event.stage) {
        case 'connected':
          newState.status = 'running'
          break

        case 'plan_ready':
          if (event.subtasks) {
            const { nodes, edges } = buildDAG(event.subtasks)
            newState.nodes = nodes
            newState.edges = edges
            newState.subtasks = event.subtasks
            newState.route = event.route ?? null
            newState.metrics = {
              ...prev.metrics,
              totalTasks: event.subtasks.length,
            }
          }
          break

        case 'task_start':
          if (event.task_id) {
            updateNodeStatus(event.task_id, 'running')
          }
          break

        case 'task_complete':
          if (event.task_id) {
            const status: TaskStatus = event.success ? 'success' : 'failed'
            updateNodeStatus(event.task_id, status, event.duration_ms, event.data, event.error)

            newTaskResults.set(event.task_id, {
              task_id: event.task_id,
              tool: event.tool ?? 'unknown',
              success: event.success ?? false,
              data: event.data,
              error: event.error,
              duration_ms: event.duration_ms ?? 0,
              status,
            })

            const completedTasks = Array.from(newTaskResults.values()).filter(t => t.success).length
            const failedTasks = Array.from(newTaskResults.values()).filter(t => !t.success).length
            const totalDuration = Array.from(newTaskResults.values()).reduce((sum, t) => sum + t.duration_ms, 0)
            const avgTaskDuration = newTaskResults.size > 0 ? totalDuration / newTaskResults.size : 0

            newState.taskResults = newTaskResults
            newState.metrics = {
              ...prev.metrics,
              completedTasks,
              failedTasks,
              totalDuration,
              avgTaskDuration,
            }
          }
          break

        case 'stage_change': {
          // Update planner/synthesizer/report status based on data.stage
          const currentStage = (event as any).data?.stage || event.stage
          if (currentStage === 'planning') {
            updateNodeStatus('planner', 'running')
          } else if (currentStage === 'executing') {
            updateNodeStatus('planner', 'success')
          } else if (currentStage === 'reasoning' || currentStage === 'reporting') {
            updateNodeStatus('synthesizer', 'running')
          }
          break
        }

        case 'reasoning':
          updateNodeStatus('planner', 'success')
          break

        case 'reporting': {
          // Find synthesizer node and update
          const synthNode = prev.nodes.find(n => n.type === 'synthesizerNode')
          if (synthNode) {
            updateNodeStatus(synthNode.id, 'success')
          }
          break
        }

        case 'complete':
          newState.status = 'completed'
          updateNodeStatus('report', 'success')

          // Mark all remaining pending tasks as skipped
          prev.nodes.forEach(node => {
            if (node.data.status === 'pending') {
              updateNodeStatus(node.id, 'skipped')
            }
          })
          break

        case 'error':
          newState.status = 'error'
          break
      }

      return { ...prev, ...newState }
    })
  }, [buildDAG, updateNodeStatus])

  // Connect to SSE
  const connect = useCallback((taskId: string, query?: string) => {
    // Disconnect existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setState(prev => ({
      ...initialState,
      taskId,
      query: query ?? prev.query,
      status: 'connecting',
    }))

    // Native EventSource cannot set an Authorization header, so the access
    // token is passed as a query parameter (the backend accepts both).
    const authToken = localStorage.getItem('auth_token')
    const streamUrl = authToken
      ? `/api/task/${taskId}/stream?token=${encodeURIComponent(authToken)}`
      : `/api/task/${taskId}/stream`
    const eventSource = new EventSource(streamUrl)
    eventSourceRef.current = eventSource
    reconnectAttemptsRef.current = 0

    eventSource.onopen = () => {
      console.log('SSE connection opened')
      reconnectAttemptsRef.current = 0
    }

    // Listen for specific events
    const eventTypes = ['connected', 'plan_ready', 'task_start', 'task_complete', 'stage_change', 'reasoning', 'reporting', 'complete', 'error']

    eventTypes.forEach(eventType => {
      eventSource.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          handleEvent({ ...data, stage: eventType })
        } catch (err) {
          console.error('Failed to parse SSE event:', err)
        }
      })
    })

    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
      eventSource.close()

      // Auto reconnect
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000)

        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`Reconnecting SSE (attempt ${reconnectAttemptsRef.current})...`)
          connect(taskId, query)
        }, delay)
      } else {
        setState(prev => ({ ...prev, status: 'error' }))
      }
    }
  }, [handleEvent])

  // Disconnect
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    setState(initialState)
  }, [])

  // Select task
  const selectTask = useCallback((taskId: string | null) => {
    setState(prev => {
      const selectedTask = taskId ? prev.taskResults.get(taskId) ?? null : null
      return { ...prev, selectedTaskId: taskId, selectedTask }
    })
  }, [])

  // Retry connection
  const retryConnection = useCallback(() => {
    if (state.taskId) {
      reconnectAttemptsRef.current = 0
      connect(state.taskId, state.query ?? undefined)
    }
  }, [state.taskId, state.query, connect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  return [
    state,
    { connect, disconnect, selectTask, retryConnection },
  ]
}
