# Copyright (c) 2026 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.
#
# SPDX-License-Identifier: MIT

:local domain "local.domain.name";
:if ($leaseBound = 1) do={
  :local hostname [:convert transform=lc $"lease-hostname"]
  :local mac $leaseActMAC
  :if ($hostname = "") do={
    :set hostname [:convert transform=lc ("device-" . [:pick $mac 9 11] . [:pick $mac 12 14] . [:pick $mac 15 17])]
  }
  :local existingDNSentry [/ip/dns/static find where name=($hostname . "." . $domain)]
  :if ($existingDNSentry != "") do={
    :local existingDNSentryIP [/ip/dns/static get $existingDNSentry address]
    :if ($existingDNSentryIP != $leaseActIP) do={
      :log info ("Hostname " . $hostname . " already exists and points to a different IP address " . $existingDNSentryIP)
      :set hostname [:convert transform=lc ($hostname . "-" . [:pick $mac 9 11] . [:pick $mac 12 14] . [:pick $mac 15 17])]
    } else={
      :log info ("Hostname " . $hostname . " already exists and points to the same IP address " . $leaseActIP)
    }
  }
  :log info ("Got IP / hostname: " . $leaseActIP . " / " . $hostname)
  :local fqdn ($hostname . "." . $domain)
  /ip/dns/static add name=$fqdn address=$leaseActIP ttl=1d comment=$fqdn
  
  # Update DHCP lease comment with DNS info
  :local leaseEntry [/ip/dhcp-server/lease find where address=$leaseActIP]
  :if ($leaseEntry != "") do={
    /ip/dhcp-server/lease set $leaseEntry comment=$fqdn
  }
} else={
  :local existingDNSentry [/ip/dns/static find where address=$leaseActIP]
  :if ($existingDNSentry != "") do={
    :local existingDNSentryName [/ip/dns/static get $existingDNSentry name]
    :log info ("Released: " . $leaseActIP . " / hostname: " . $existingDNSentryName)
    /ip/dns/static remove $existingDNSentry
  }
  
  # Clear DHCP lease comment when released
  :local leaseEntry [/ip/dhcp-server/lease find where address=$leaseActIP]
  :if ($leaseEntry != "") do={
    /ip/dhcp-server/lease set $leaseEntry comment=""
  }
}