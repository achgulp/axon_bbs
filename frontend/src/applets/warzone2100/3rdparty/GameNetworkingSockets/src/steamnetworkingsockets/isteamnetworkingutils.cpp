//====== Copyright Valve Corporation, All rights reserved. ====================
//
// Purpose: misc networking utilities
//
//=============================================================================

#include <steam/isteamnetworkingutils.h>

#if defined( STEAMNETWORKINGSOCKETS_STATIC_LINK ) || defined(STEAMNETWORKINGSOCKETS_FOREXPORT) || defined( STEAMNETWORKINGSOCKETS_STANDALONELIB )

	void SteamNetworkingIPAddr::ToString(char* buf, size_t cbBuf, bool bWithPort) const { SteamNetworkingIPAddr_ToString(this, buf, cbBuf, bWithPort); }
	bool SteamNetworkingIPAddr::ParseString(const char* pszStr) { return SteamNetworkingIPAddr_ParseString(this, pszStr); }
	ESteamNetworkingFakeIPType SteamNetworkingIPAddr::GetFakeIPType() const { return SteamNetworkingIPAddr_GetFakeIPType(this); }
	void SteamNetworkingIdentity::ToString(char* buf, size_t cbBuf) const { SteamNetworkingIdentity_ToString(this, buf, cbBuf); }
	bool SteamNetworkingIdentity::ParseString(const char* pszStr) { return SteamNetworkingIdentity_ParseString(this, sizeof(*this), pszStr); }

#elif defined( STEAMNETWORKINGSOCKETS_STEAMAPI )

	// Using steamworks SDK - go through SteamNetworkingUtils()
	void SteamNetworkingIPAddr::ToString(char* buf, size_t cbBuf, bool bWithPort) const { SteamNetworkingUtils()->SteamNetworkingIPAddr_ToString(*this, buf, cbBuf, bWithPort); }
	bool SteamNetworkingIPAddr::ParseString(const char* pszStr) { return SteamNetworkingUtils()->SteamNetworkingIPAddr_ParseString(this, pszStr); }
	ESteamNetworkingFakeIPType SteamNetworkingIPAddr::GetFakeIPType() const { return SteamNetworkingUtils()->SteamNetworkingIPAddr_GetFakeIPType(*this); }
	void SteamNetworkingIdentity::ToString(char* buf, size_t cbBuf) const { SteamNetworkingUtils()->SteamNetworkingIdentity_ToString(*this, buf, cbBuf); }
	bool SteamNetworkingIdentity::ParseString(const char* pszStr) { return SteamNetworkingUtils()->SteamNetworkingIdentity_ParseString(this, pszStr); }

#else
	#error "Invalid config"
#endif
