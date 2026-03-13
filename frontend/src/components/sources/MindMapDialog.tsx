'use client'

import { useState, useEffect, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  Brain,
  Download,
  ZoomIn,
  ZoomOut,
  ChevronDown,
  ChevronRight,
  Maximize2,
  Minimize2,
  RefreshCw,
} from 'lucide-react'
import apiClient from '@/lib/api/client'

interface MindMapNode {
  id: string
  label: string
  type: 'root' | 'main' | 'sub' | 'detail'
  children?: MindMapNode[]
}

interface MindMapDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceId?: string
  sourceName?: string
  notebookId?: string
  notebookName?: string
  mode?: 'source' | 'notebook'
}

interface NodePosition {
  x: number
  y: number
  width: number
  height: number
}

export function MindMapDialog({
  open,
  onOpenChange,
  sourceId,
  sourceName,
  notebookId,
  notebookName,
  mode = 'source',
}: MindMapDialogProps) {
  const [loading, setLoading] = useState(false)
  const [mindMapData, setMindMapData] = useState<MindMapNode | null>(null)
  const [zoom, setZoom] = useState(0.9)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['root']))
  const [fullscreen, setFullscreen] = useState(false)
  const [nodePositions, setNodePositions] = useState<Map<string, NodePosition>>(new Map())
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  useEffect(() => {
    if (open && !mindMapData) {
      generateMindMap()
    }
  }, [open])

  // Update node positions after render
  useEffect(() => {
    if (mindMapData) {
      const positions = new Map<string, NodePosition>()
      nodeRefs.current.forEach((element, id) => {
        const rect = element.getBoundingClientRect()
        const parent = element.offsetParent as HTMLElement
        if (parent) {
          positions.set(id, {
            x: element.offsetLeft,
            y: element.offsetTop,
            width: rect.width,
            height: rect.height,
          })
        }
      })
      setNodePositions(positions)
    }
  }, [mindMapData, expandedNodes, zoom])

  const generateMindMap = async () => {
    setLoading(true)
    try {
      const endpoint = mode === 'source' 
        ? `/sources/${sourceId}/mindmap`
        : `/notebooks/${notebookId}/mindmap`
      
      const response = await apiClient.post(endpoint)
      const data = response.data

      setMindMapData(data.root)

      // Auto-expand root and first level
      const newExpanded = new Set<string>(['root'])
      if (data.root.children) {
        data.root.children.forEach((child: MindMapNode) => {
          newExpanded.add(child.id)
        })
      }
      setExpandedNodes(newExpanded)
    } catch (error: any) {
      console.error('Failed to generate mind map:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate mind map'
      alert(`Failed to generate mind map: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleNode = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId)
    } else {
      newExpanded.add(nodeId)
    }
    setExpandedNodes(newExpanded)
  }

  const expandAll = () => {
    const allIds = new Set<string>()
    const collectIds = (node: MindMapNode) => {
      allIds.add(node.id)
      node.children?.forEach(collectIds)
    }
    if (mindMapData) collectIds(mindMapData)
    setExpandedNodes(allIds)
  }

  const collapseAll = () => {
    setExpandedNodes(new Set(['root']))
  }

  const renderConnections = () => {
    const connections: React.ReactElement[] = []

    const processNode = (node: MindMapNode) => {
      const isExpanded = expandedNodes.has(node.id)
      if (!isExpanded || !node.children || node.children.length === 0) return

      const parentPos = nodePositions.get(node.id)
      if (!parentPos) return

      node.children.forEach((child) => {
        const childPos = nodePositions.get(child.id)
        if (!childPos) return

        // Calculate connection points
        const startX = parentPos.x + parentPos.width
        const startY = parentPos.y + parentPos.height / 2
        const endX = childPos.x
        const endY = childPos.y + childPos.height / 2

        // Create curved path
        const controlX = startX + (endX - startX) / 2
        const path = `M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`

        connections.push(
          <path
            key={`${node.id}-${child.id}`}
            d={path}
            fill="none"
            stroke="rgb(147 197 253)"
            strokeWidth="2"
            className="dark:stroke-blue-700"
          />
        )

        processNode(child)
      })
    }

    if (mindMapData) {
      processNode(mindMapData)
    }

    return connections
  }

  const renderNode = (node: MindMapNode, level: number = 0): React.ReactElement => {
    const isExpanded = expandedNodes.has(node.id)
    const hasChildren = node.children && node.children.length > 0

    const getNodeStyle = () => {
      if (hasChildren) {
        return {
          bg: 'bg-blue-100 dark:bg-blue-900/30',
          border: 'border-blue-300 dark:border-blue-700',
          text: 'text-blue-900 dark:text-blue-100',
          hover: 'hover:bg-blue-200 dark:hover:bg-blue-900/50',
        }
      } else {
        return {
          bg: 'bg-teal-100 dark:bg-teal-900/30',
          border: 'border-teal-300 dark:border-teal-700',
          text: 'text-teal-900 dark:text-teal-100',
          hover: 'hover:bg-teal-200 dark:hover:bg-teal-900/50',
        }
      }
    }

    const style = getNodeStyle()

    return (
      <div key={node.id} className="flex items-center gap-16">
        <div
          ref={(el) => {
            if (el) nodeRefs.current.set(node.id, el)
          }}
          className={`
            relative rounded-lg px-4 py-2.5 border
            ${style.bg} ${style.border} ${style.text}
            ${hasChildren ? 'cursor-pointer' : ''}
            ${style.hover}
            transition-all duration-200
            flex items-center gap-2
            text-sm font-medium
            shadow-sm
            min-w-[180px]
            max-w-[400px]
          `}
          onClick={() => hasChildren && toggleNode(node.id)}
        >
          <span className="flex-1 leading-snug break-words">{node.label}</span>
          {hasChildren && (
            <div className="flex-shrink-0">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 opacity-60" />
              ) : (
                <ChevronRight className="h-4 w-4 opacity-60" />
              )}
            </div>
          )}
        </div>

        {hasChildren && isExpanded && node.children && node.children.length > 0 && (
          <div className="flex flex-col gap-8">
            {node.children.map((child) => (
              <div key={child.id}>{renderNode(child, level + 1)}</div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const title = mode === 'source' ? sourceName : notebookName
  const displayTitle = mode === 'source' ? 'Source Mind Map' : 'Notebook Study Guide'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={`${
          fullscreen ? 'max-w-[98vw] h-[98vh]' : 'max-w-[90vw] max-h-[90vh]'
        } overflow-hidden flex flex-col transition-all duration-300`}
      >
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-3 text-xl">
            <Brain className="h-5 w-5 text-blue-600" />
            <span>{displayTitle}</span>
          </DialogTitle>
          <DialogDescription className="text-sm">{title}</DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2 py-2 border-b flex-wrap">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setZoom(Math.min(zoom + 0.1, 3))}
              className="h-8 w-8 p-0"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setZoom(1)} className="h-8 px-2">
              <span className="text-xs font-medium min-w-[50px] text-center text-gray-600 dark:text-gray-400">
                {Math.round(zoom * 100)}%
              </span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setZoom(Math.max(zoom - 0.1, 0.3))}
              className="h-8 w-8 p-0"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
          </div>

          <div className="w-px h-6 bg-gray-300 dark:bg-gray-700" />

          <Button variant="ghost" size="sm" onClick={expandAll}>
            <ChevronDown className="h-4 w-4 mr-1" />
            Expand all
          </Button>
          <Button variant="ghost" size="sm" onClick={collapseAll}>
            <ChevronRight className="h-4 w-4 mr-1" />
            Collapse all
          </Button>

          <div className="w-px h-6 bg-gray-300 dark:bg-gray-700" />

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMindMapData(null)
              generateMindMap()
            }}
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Regenerate
          </Button>

          <div className="flex-1" />

          <Button variant="ghost" size="sm" onClick={() => setFullscreen(!fullscreen)}>
            {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>

          <Button variant="ghost" size="sm" disabled className="opacity-50">
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>

        <div className="flex-1 overflow-auto p-8 bg-white dark:bg-gray-950 relative">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4">
                <LoadingSpinner size="lg" />
                <div className="space-y-2">
                  <p className="text-base font-medium text-gray-800 dark:text-gray-200">
                    Generating mind map...
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Analyzing content with AI
                  </p>
                </div>
              </div>
            </div>
          ) : mindMapData ? (
            <div className="relative">
              <svg
                className="absolute top-0 left-0 pointer-events-none"
                style={{
                  width: '100%',
                  height: '100%',
                  zIndex: 0,
                }}
              >
                {renderConnections()}
              </svg>
              <div
                className="relative"
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: 'top left',
                  zIndex: 1,
                }}
              >
                {renderNode(mindMapData)}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4">
                <Brain className="h-12 w-12 text-gray-400 mx-auto" />
                <div className="space-y-2">
                  <p className="text-base font-medium text-gray-800 dark:text-gray-200">
                    No content available
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {mode === 'source' 
                      ? 'This source has no content to generate a mind map'
                      : 'Add sources to your notebook to generate a study guide'}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={generateMindMap}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
