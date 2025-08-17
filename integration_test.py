"""
Integration test for the Backlink Indexing System
"""

import asyncio
from backlink_indexer.core.config import IndexingConfig
from backlink_indexer.core.coordinator import BacklinkIndexingCoordinator


async def test_backlink_indexer():
    """Test the backlink indexing system"""
    
    print("🚀 Starting Backlink Indexer Integration Test")
    
    # Create configuration
    config = IndexingConfig(
        max_concurrent_browsers=5,
        headless_mode=True,
        mock_mode=True,  # Enable mock mode for testing
        social_bookmarking_enabled=True,
        rss_distribution_enabled=True,
        web2_posting_enabled=True,
        success_threshold=0.8
    )
    
    print(f"📝 Configuration created with {len([m for m in ['social_bookmarking', 'rss_distribution', 'web2_posting'] if getattr(config, f'{m}_enabled')])} methods enabled")
    
    # Initialize coordinator
    coordinator = BacklinkIndexingCoordinator(config)
    print("🎯 Coordinator initialized")
    
    # Test URLs
    test_urls = [
        "https://example.com/article1",
        "https://example.com/article2"
    ]
    
    print(f"🔗 Processing {len(test_urls)} test URLs")
    
    try:
        # Process URLs
        results = await coordinator.process_url_collection(
            test_urls, 
            metadata={'title': 'Test Article', 'topic': 'technology'}
        )
        
        print("\n📊 RESULTS:")
        print(f"✅ Total URLs: {results['total_urls']}")
        print(f"✅ Successful: {results['successful_urls']}")
        print(f"⚠️  Partial Success: {results['partial_success_urls']}")
        print(f"❌ Failed: {results['failed_urls']}")
        print(f"📈 Overall Success Rate: {results['overall_success_rate']:.1%}")
        
        print("\n🔍 METHOD PERFORMANCE:")
        for method, stats in results['method_performance'].items():
            print(f"  {method}: {stats['success_rate']:.1%} ({stats['successful_attempts']}/{stats['total_attempts']})")
        
        # Get performance summary
        summary = coordinator.get_performance_summary()
        print(f"\n💹 SYSTEM STATS:")
        print(f"  Total URLs Processed: {summary['overall_stats']['total_urls_processed']}")
        print(f"  System Success Rate: {(summary['overall_stats']['successful_urls'] / summary['overall_stats']['total_urls_processed']):.1%}")
        
        print("\n✅ Integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        
    finally:
        # Cleanup
        await coordinator.shutdown()
        print("🧹 Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_backlink_indexer())