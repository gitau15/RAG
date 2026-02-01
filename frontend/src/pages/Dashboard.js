import React, { useState, useEffect } from 'react';
import { BookOpenIcon, DocumentTextIcon, ChatBubbleLeftRightIcon, FolderIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

export default function Dashboard() {
  const [stats, setStats] = useState({
    collections: 0,
    documents: 0,
    queries: 0,
    totalChunks: 0
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      // Mock data for now - replace with actual API calls
      setStats({
        collections: 5,
        documents: 24,
        queries: 156,
        totalChunks: 1247
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      name: 'Collections',
      value: stats.collections,
      icon: FolderIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Documents',
      value: stats.documents,
      icon: DocumentTextIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Total Queries',
      value: stats.queries,
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'Document Chunks',
      value: stats.totalChunks,
      icon: BookOpenIcon,
      color: 'bg-orange-500',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Welcome to your RAG Platform dashboard</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => (
          <div key={card.name} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center">
              <div className={`${card.color} p-3 rounded-lg`}>
                <card.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">{card.name}</p>
                <p className="text-2xl font-bold text-white">{card.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <button className="w-full flex items-center justify-between p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
              <span className="text-white">Upload New Document</span>
              <DocumentTextIcon className="h-5 w-5 text-gray-400" />
            </button>
            <button className="w-full flex items-center justify-between p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
              <span className="text-white">Start New Chat</span>
              <ChatBubbleLeftRightIcon className="h-5 w-5 text-gray-400" />
            </button>
            <button className="w-full flex items-center justify-between p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
              <span className="text-white">Create Collection</span>
              <FolderIcon className="h-5 w-5 text-gray-400" />
            </button>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>
          <div className="space-y-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="h-2 w-2 bg-green-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-white">New document uploaded</p>
                <p className="text-xs text-gray-400">2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="h-2 w-2 bg-blue-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-white">Collection created</p>
                <p className="text-xs text-gray-400">1 hour ago</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="h-2 w-2 bg-purple-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-white">Query processed</p>
                <p className="text-xs text-gray-400">3 hours ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}