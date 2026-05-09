Check HIVE system status. Run these checks and report:
1. Is Hermes gateway running? `systemctl --user is-active hermes-gateway 2>/dev/null || echo "not systemd"`
2. Is OD daemon running? `curl -sf http://localhost:7456/api/skills > /dev/null && echo "OD: up" || echo "OD: down"`
3. Is NIM proxy running? `curl -sf http://localhost:7457/health && echo "proxy: up" || echo "proxy: down"`
4. Hermes default model: `grep "default:" ~/.hermes/config.yaml | head -1`
5. Last 3 memory entries: `tail -3 ~/HIVE/memory/sessions.log 2>/dev/null`
Report all results concisely.
