"""
DLQ Replay Tool
===============

Command-line tool for manually replaying DLQ messages.
"""

import asyncio
import argparse
import logging
from typing import Optional

from .dlq_manager import DLQManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DLQReplayTool:
    """Tool for replaying DLQ messages"""
    
    def __init__(self, dlq_manager: DLQManager):
        self.dlq_manager = dlq_manager
    
    async def list_messages(self, channel: Optional[str] = None) -> None:
        """
        List all messages in DLQ
        
        Args:
            channel: Filter by channel (optional)
        """
        if channel:
            messages = self.dlq_manager.get_messages_by_channel(channel)
            print(f"\nMessages in DLQ for channel '{channel}':")
        else:
            messages = self.dlq_manager.get_all_messages()
            print(f"\nAll messages in DLQ:")
        
        if not messages:
            print("  No messages found.")
            return
        
        print(f"  Total: {len(messages)} messages\n")
        
        for msg in messages:
            print(f"  ID: {msg.id}")
            print(f"    Channel: {msg.channel}")
            print(f"    Subscriber: {msg.subscriber_id}")
            print(f"    Error: {msg.error_type}: {msg.error_message}")
            print(f"    Retries: {msg.retry_count}/{msg.max_retries}")
            print(f"    Failed at: {msg.failure_timestamp}")
            print(f"    Retryable: {msg.is_retryable()}")
            print()
    
    async def show_stats(self) -> None:
        """Show DLQ statistics"""
        stats = self.dlq_manager.get_stats()
        
        print("\nDLQ Statistics:")
        print(f"  Total Messages: {stats['total_messages']}")
        print(f"  Retryable Messages: {stats['retryable_messages']}")
        print(f"  Total Failures: {stats['total_failures']}")
        print(f"  Total Retries: {stats['total_retries']}")
        print(f"  Total Successes: {stats['total_successes']}")
        print(f"  Total Discarded: {stats['total_discarded']}")
        
        if stats['failures_by_channel']:
            print("\n  Failures by Channel:")
            for channel, count in stats['failures_by_channel'].items():
                print(f"    {channel}: {count}")
        
        if stats['failures_by_subscriber']:
            print("\n  Failures by Subscriber:")
            for subscriber, count in stats['failures_by_subscriber'].items():
                print(f"    {subscriber}: {count}")
        
        print()
    
    async def replay_message(self, message_id: str) -> None:
        """
        Replay a specific message
        
        Args:
            message_id: Message ID to replay
        """
        msg = self.dlq_manager.get_message(message_id)
        
        if not msg:
            print(f"Error: Message '{message_id}' not found in DLQ")
            return
        
        print(f"\nReplaying message: {message_id}")
        print(f"  Channel: {msg.channel}")
        print(f"  Error: {msg.error_message}")
        
        # Note: Actual replay requires broker and subscriber setup
        # This is a demonstration of the API
        print("\n  Manual replay requires subscriber callback setup.")
        print("  Use the DLQManager.retry_message() API in your application.")
    
    async def replay_channel(self, channel: str) -> None:
        """
        Replay all messages for a channel
        
        Args:
            channel: Channel name
        """
        messages = self.dlq_manager.get_messages_by_channel(channel)
        
        if not messages:
            print(f"No messages found for channel '{channel}'")
            return
        
        print(f"\nReplaying {len(messages)} messages for channel '{channel}'")
        
        # Note: Actual replay requires broker and subscriber setup
        print("  Manual replay requires subscriber callback setup.")
        print("  Use the DLQManager.replay_all() API in your application.")
    
    async def clear_successful(self) -> None:
        """Clear messages that have been successfully processed"""
        messages = self.dlq_manager.get_all_messages()
        non_retryable = [msg for msg in messages if not msg.is_retryable()]
        
        print(f"\nFound {len(non_retryable)} non-retryable messages")
        print("  (These have exceeded max retries)")
        print("\n  Use DLQ cleanup loop for automatic removal after retention period.")


async def main():
    """Main entry point for replay tool"""
    parser = argparse.ArgumentParser(
        description="DLQ Replay Tool - Manage and replay failed messages"
    )
    
    parser.add_argument(
        '--storage-path',
        default='./dlq',
        help='DLQ storage directory (default: ./dlq)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List DLQ messages')
    list_parser.add_argument('--channel', help='Filter by channel')
    
    # Stats command
    subparsers.add_parser('stats', help='Show DLQ statistics')
    
    # Replay command
    replay_parser = subparsers.add_parser('replay', help='Replay a message')
    replay_parser.add_argument('message_id', help='Message ID to replay')
    
    # Replay channel command
    replay_channel_parser = subparsers.add_parser(
        'replay-channel',
        help='Replay all messages for a channel'
    )
    replay_channel_parser.add_argument('channel', help='Channel name')
    
    # Clear command
    subparsers.add_parser('clear', help='Clear non-retryable messages')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize DLQ manager
    dlq_manager = DLQManager(storage_path=args.storage_path)
    await dlq_manager.start()
    
    try:
        tool = DLQReplayTool(dlq_manager)
        
        if args.command == 'list':
            await tool.list_messages(channel=args.channel)
        
        elif args.command == 'stats':
            await tool.show_stats()
        
        elif args.command == 'replay':
            await tool.replay_message(args.message_id)
        
        elif args.command == 'replay-channel':
            await tool.replay_channel(args.channel)
        
        elif args.command == 'clear':
            await tool.clear_successful()
    
    finally:
        await dlq_manager.stop()


if __name__ == '__main__':
    asyncio.run(main())
