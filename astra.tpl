-- Astra Slonik Mod

-- during revival and testing
-- log.set({ stdout = true, debug = true, syslog = "astra", filename = "/tmp/astrasm.log", })
-- after revival and testing
log.set({ stdout = true, debug = false, syslog = "astra", filename = "/tmp/astra.log" })

-- =========================================================================
-- [ SECTION 1: ABERTIS PID CHANNELS ]
-- =========================================================================

-- Helper Text: This table maps the Abertis PID to its specific Enigma2 Stream Reference.
local abertis_list = {
    { pid = "301",  ref = "1:0:1:515:EA63:0:CE42D85:0:0:0:" },
    { pid = "303",  ref = "1:0:1:517:EA63:0:CE42D85:0:0:0:" },
    { pid = "420",  ref = "1:0:1:58C:EA64:0:CE42D9D:0:0:0:" },
    { pid = "421",  ref = "1:0:1:58D:EA64:0:CE42D9D:0:0:0:" },
    { pid = "423",  ref = "1:0:1:58F:EA64:0:CE42D9D:0:0:0:" },
    { pid = "431",  ref = "1:0:1:597:EA64:0:CE42D9D:0:0:0:" },
    { pid = "433",  ref = "1:0:1:599:EA64:0:CE42D9D:0:0:0:" },
    { pid = "440",  ref = "1:0:1:5A0:EA64:0:CE42D9D:0:0:0:" },
    { pid = "701",  ref = "1:0:1:6A5:EA67:0:CE4B104:0:0:0:" },
    { pid = "702",  ref = "1:0:1:6A6:EA67:0:CE4B104:0:0:0:" },
    { pid = "703",  ref = "1:0:1:6A7:EA67:0:CE4B104:0:0:0:" },
    { pid = "801",  ref = "1:0:1:709:EA7C:0:CE4ACEE:0:0:0:" },
    { pid = "2025", ref = "1:0:1:BD1:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2026", ref = "1:0:1:BD2:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2027", ref = "1:0:1:BD3:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2028", ref = "1:0:1:BD4:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2035", ref = "1:0:1:BDB:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2036", ref = "1:0:1:BDC:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2037", ref = "1:0:1:BDD:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2038", ref = "1:0:1:BDE:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2050", ref = "1:0:1:BEA:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2060", ref = "1:0:1:BF4:EA74:1:CE42BD6:0:0:0:" },
    { pid = "2270", ref = "1:0:1:CC6:EA76:1:CE42C26:0:0:0:" },
    { pid = "2271", ref = "1:0:1:CC7:EA76:1:CE42C26:0:0:0:" },
    { pid = "2272", ref = "1:0:1:CC8:EA76:1:CE42C26:0:0:0:" },
    { pid = "2273", ref = "1:0:1:CC9:EA76:1:CE42C26:0:0:0:" },
    { pid = "2274", ref = "1:0:1:CCA:EA76:1:CE42C26:0:0:0:" },
    { pid = "2281", ref = "1:0:1:CD1:EA76:1:CE42C26:0:0:0:" },
    { pid = "2282", ref = "1:0:1:CD2:EA76:1:CE42C26:0:0:0:" },
    { pid = "2283", ref = "1:0:1:CD3:EA76:1:CE42C26:0:0:0:" },
    { pid = "2284", ref = "1:0:1:CD4:EA76:1:CE42C26:0:0:0:" },
    { pid = "2301", ref = "1:0:1:CE5:EA77:0:CE42C53:0:0:0:" },
    { pid = "2302", ref = "1:0:1:CE6:EA77:0:CE42C53:0:0:0:" },
    { pid = "2303", ref = "1:0:1:CE7:EA77:0:CE42C53:0:0:0:" },
    { pid = "2304", ref = "1:0:1:CE8:EA77:0:CE42C53:0:0:0:" },
    { pid = "2305", ref = "1:0:1:CE9:EA77:0:CE42C53:0:0:0:" },
    { pid = "2306", ref = "1:0:1:CEA:EA77:0:CE42C53:0:0:0:" },
    { pid = "2307", ref = "1:0:1:CEB:EA77:0:CE42C53:0:0:0:" },
    { pid = "2308", ref = "1:0:1:CEC:EA77:0:CE42C53:0:0:0:" },
    { pid = "2520", ref = "1:0:1:DC0:EA79:1:CE42C76:0:0:0:" },
    { pid = "2521", ref = "1:0:1:DC1:EA79:1:CE42C76:0:0:0:" },
    { pid = "2522", ref = "1:0:1:DC2:EA79:1:CE42C76:0:0:0:" },
    { pid = "2523", ref = "1:0:1:DC3:EA79:1:CE42C76:0:0:0:" },
    { pid = "2524", ref = "1:0:1:DC4:EA79:1:CE42C76:0:0:0:" },
    { pid = "2531", ref = "1:0:1:DCB:EA79:1:CE42C76:0:0:0:" },
    { pid = "2532", ref = "1:0:1:DCC:EA79:1:CE42C76:0:0:0:" },
    { pid = "2533", ref = "1:0:1:DCD:EA79:1:CE42C76:0:0:0:" },
    { pid = "2534", ref = "1:0:1:DCE:EA79:1:CE42C76:0:0:0:" },
    { pid = "3701", ref = "1:0:1:125D:EA7B:1:CE4AF69:0:0:0:" },
    { pid = "8000", ref = "1:0:1:3E8:EA61:0:CE4B17F:0:0:0:" },
    { pid = "8001", ref = "1:0:1:3E9:EA62:0:CE4B157:0:0:0:" },
    { pid = "8002", ref = "1:0:1:3EA:EA62:0:CE4B157:0:0:0:" },
    { pid = "8003", ref = "1:0:1:3EB:EA62:0:CE4B157:0:0:0:" },
    { pid = "8004", ref = "1:0:1:3EC:EA61:0:CE4B17F:0:0:0:" },
    { pid = "8005", ref = "1:0:1:3ED:EA61:0:CE4B17F:0:0:0:" },
    { pid = "8006", ref = "1:0:1:3EE:EA61:0:CE4B17F:0:0:0:" },
}

-- Helper Text: Dynamically create Abertis channels using the table above.
for _, item in ipairs(abertis_list) do
    make_channel({
        name = "Abertis PID " .. item.pid,
        input = {
            "http://localhost:8001/" .. item.ref,
        },
        transform = {{
            format = "pipe",
            command = "/etc/astra/scripts/abertis " .. item.pid,
        }},
        output = {
            "http://0.0.0.0:9999/abertis/pid" .. item.pid,
        },
    })
end





-- [ T2-MI Transponders GENERATED CONFIG ] --
