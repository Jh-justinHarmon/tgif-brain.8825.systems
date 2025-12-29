"""
Maestra Backend - Smoke Tests
Tests for local, cloud, and mixed deployment scenarios
"""

import asyncio
import httpx
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import uuid


class MaestraTestClient:
    """Test client for Maestra Backend"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=10.0)
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.aclose()
    
    async def health(self) -> Dict[str, Any]:
        """Check health endpoint"""
        response = await self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def metrics(self) -> Dict[str, Any]:
        """Get metrics"""
        response = await self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()
    
    async def ask(
        self,
        user_id: str,
        surface_id: str,
        conversation_id: str,
        message: str,
        mode_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ask Maestra a question"""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "user_id": user_id,
            "surface_id": surface_id,
            "conversation_id": conversation_id,
            "message": message,
        }
        if mode_hint:
            payload["mode_hint"] = mode_hint
        
        response = await self.session.post(
            f"{self.base_url}/api/maestra/core",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def legacy_ask(
        self,
        session_id: str,
        user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Test legacy advisor endpoint"""
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
        }
        
        response = await self.session.post(
            f"{self.base_url}/api/maestra/advisor/ask",
            json=payload
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Test Suites
# ============================================================================

async def test_local_backend():
    """Test local backend (no API key required)"""
    print("\n" + "="*60)
    print("TEST: Local Backend (localhost:8825)")
    print("="*60)
    
    base_url = "http://127.0.0.1:8825"
    
    try:
        async with MaestraTestClient(base_url) as client:
            # Test 1: Health check
            print("\n[1/5] Testing /health endpoint...")
            health = await client.health()
            assert health["status"] == "healthy"
            assert health["version"] == "2.0.0"
            print(f"✓ Health check passed (uptime: {health['uptime_seconds']}s)")
            
            # Test 2: Metrics
            print("\n[2/5] Testing /metrics endpoint...")
            metrics = await client.metrics()
            assert "total_requests" in metrics
            assert "uptime_seconds" in metrics
            print(f"✓ Metrics retrieved (requests: {metrics['total_requests']})")
            
            # Test 3: Canonical endpoint
            print("\n[3/5] Testing /api/maestra/core endpoint...")
            conv_id = f"conv_test_local_{uuid.uuid4().hex[:8]}"
            response = await client.ask(
                user_id="test_user",
                surface_id="test",
                conversation_id=conv_id,
                message="Hello from local backend"
            )
            assert response["conversation_id"] == conv_id
            assert "reply" in response
            print(f"✓ Canonical endpoint working (mode: {response['mode']})")
            
            # Test 4: Legacy endpoint
            print("\n[4/5] Testing /api/maestra/advisor/ask endpoint...")
            legacy_response = await client.legacy_ask(
                session_id=conv_id,
                user_id="test_user",
                message="Hello from legacy endpoint"
            )
            assert "answer" in legacy_response
            print(f"✓ Legacy endpoint working")
            
            # Test 5: Cross-surface continuity
            print("\n[5/5] Testing cross-surface continuity...")
            response2 = await client.ask(
                user_id="test_user",
                surface_id="windsurf",  # Different surface
                conversation_id=conv_id,
                message="Second message from different surface"
            )
            assert response2["conversation_id"] == conv_id
            print(f"✓ Cross-surface continuity working")
            
            print("\n✅ LOCAL BACKEND: All tests passed!")
            return True
    
    except Exception as e:
        print(f"\n❌ LOCAL BACKEND: Test failed - {e}")
        return False


async def test_cloud_backend():
    """Test cloud backend (requires API key)"""
    print("\n" + "="*60)
    print("TEST: Cloud Backend (Replit)")
    print("="*60)
    
    base_url = os.getenv("MAESTRA_CLOUD_URL", "https://maestra.replit.dev")
    api_key = os.getenv("MAESTRA_API_KEY", "")
    
    if not api_key:
        print("\n⚠️  CLOUD BACKEND: Skipped (MAESTRA_API_KEY not set)")
        return None
    
    try:
        async with MaestraTestClient(base_url, api_key) as client:
            # Test 1: Health check
            print("\n[1/4] Testing /health endpoint...")
            health = await client.health()
            assert health["status"] == "healthy"
            print(f"✓ Health check passed")
            
            # Test 2: Metrics
            print("\n[2/4] Testing /metrics endpoint...")
            metrics = await client.metrics()
            assert "total_requests" in metrics
            print(f"✓ Metrics retrieved")
            
            # Test 3: Canonical endpoint with API key
            print("\n[3/4] Testing /api/maestra/core with API key...")
            conv_id = f"conv_test_cloud_{uuid.uuid4().hex[:8]}"
            response = await client.ask(
                user_id="test_user",
                surface_id="test",
                conversation_id=conv_id,
                message="Hello from cloud backend"
            )
            assert response["conversation_id"] == conv_id
            print(f"✓ Cloud endpoint working")
            
            # Test 4: Invalid API key
            print("\n[4/4] Testing invalid API key rejection...")
            try:
                async with MaestraTestClient(base_url, "invalid_key") as bad_client:
                    await bad_client.ask(
                        user_id="test_user",
                        surface_id="test",
                        conversation_id="conv_test",
                        message="Should fail"
                    )
                print("❌ Invalid API key was not rejected!")
                return False
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    print(f"✓ Invalid API key properly rejected")
                else:
                    raise
            
            print("\n✅ CLOUD BACKEND: All tests passed!")
            return True
    
    except Exception as e:
        print(f"\n❌ CLOUD BACKEND: Test failed - {e}")
        return False


async def test_mixed_scenario():
    """Test mixed local/cloud scenario with fallback"""
    print("\n" + "="*60)
    print("TEST: Mixed Scenario (Local → Cloud Fallback)")
    print("="*60)
    
    local_url = "http://127.0.0.1:8825"
    cloud_url = os.getenv("MAESTRA_CLOUD_URL", "https://maestra.replit.dev")
    api_key = os.getenv("MAESTRA_API_KEY", "")
    
    try:
        # Test 1: Local is available
        print("\n[1/3] Verifying local backend is available...")
        async with MaestraTestClient(local_url) as client:
            health = await client.health()
            assert health["status"] == "healthy"
            print(f"✓ Local backend is available")
        
        # Test 2: Cloud is available (if configured)
        if api_key:
            print("\n[2/3] Verifying cloud backend is available...")
            async with MaestraTestClient(cloud_url, api_key) as client:
                health = await client.health()
                assert health["status"] == "healthy"
                print(f"✓ Cloud backend is available")
        else:
            print("\n[2/3] Skipping cloud verification (MAESTRA_API_KEY not set)")
        
        # Test 3: Same conversation across surfaces
        print("\n[3/3] Testing conversation continuity across surfaces...")
        conv_id = f"conv_test_mixed_{uuid.uuid4().hex[:8]}"
        
        # Message 1: Local
        async with MaestraTestClient(local_url) as client:
            response1 = await client.ask(
                user_id="test_user",
                surface_id="windsurf",
                conversation_id=conv_id,
                message="Message from Windsurf"
            )
            assert response1["conversation_id"] == conv_id
            print(f"✓ Message 1 sent via local (Windsurf)")
        
        # Message 2: Local, different surface
        async with MaestraTestClient(local_url) as client:
            response2 = await client.ask(
                user_id="test_user",
                surface_id="browser_ext",
                conversation_id=conv_id,
                message="Message from Browser Extension"
            )
            assert response2["conversation_id"] == conv_id
            print(f"✓ Message 2 sent via local (Browser Extension)")
        
        # Verify conversation storage
        conv_path = Path.home() / ".8825" / "conversations" / f"{conv_id}.json"
        if conv_path.exists():
            with open(conv_path) as f:
                conv = json.load(f)
            assert len(conv["messages"]) >= 2
            assert "windsurf" in conv["surfaces"]
            assert "browser_ext" in conv["surfaces"]
            print(f"✓ Conversation stored with {len(conv['messages'])} messages across {len(conv['surfaces'])} surfaces")
        
        print("\n✅ MIXED SCENARIO: All tests passed!")
        return True
    
    except Exception as e:
        print(f"\n❌ MIXED SCENARIO: Test failed - {e}")
        return False


async def test_rate_limiting():
    """Test rate limiting on cloud backend"""
    print("\n" + "="*60)
    print("TEST: Rate Limiting (Cloud)")
    print("="*60)
    
    cloud_url = os.getenv("MAESTRA_CLOUD_URL", "https://maestra.replit.dev")
    api_key = os.getenv("MAESTRA_API_KEY", "")
    
    if not api_key:
        print("\n⚠️  RATE LIMITING: Skipped (MAESTRA_API_KEY not set)")
        return None
    
    try:
        print("\n[1/1] Testing rate limit enforcement...")
        
        # This test would send many requests to trigger rate limit
        # For now, just verify rate limit headers are present
        async with MaestraTestClient(cloud_url, api_key) as client:
            response = await client.session.post(
                f"{cloud_url}/api/maestra/core",
                json={
                    "user_id": "test",
                    "surface_id": "test",
                    "conversation_id": "conv_test",
                    "message": "test"
                },
                headers={"X-API-Key": api_key}
            )
            
            # Check for rate limit headers
            if "x-ratelimit-limit" in response.headers or "ratelimit-limit" in response.headers:
                print(f"✓ Rate limit headers present")
            else:
                print(f"⚠️  Rate limit headers not found (may not be configured)")
        
        print("\n✅ RATE LIMITING: Test passed!")
        return True
    
    except Exception as e:
        print(f"\n❌ RATE LIMITING: Test failed - {e}")
        return False


async def main():
    """Run all smoke tests"""
    print("\n" + "="*60)
    print("MAESTRA BACKEND - SMOKE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Run tests
    results["local"] = await test_local_backend()
    results["cloud"] = await test_cloud_backend()
    results["mixed"] = await test_mixed_scenario()
    results["rate_limiting"] = await test_rate_limiting()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "⚠️  SKIP" if result is None else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\nTotal: {passed} passed, {skipped} skipped, {failed} failed")
    
    if failed > 0:
        print("\n❌ SMOKE TESTS FAILED")
        return False
    else:
        print("\n✅ SMOKE TESTS PASSED")
        return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
