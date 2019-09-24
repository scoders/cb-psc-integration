rule microsoft {
    meta:
        score = 5
    strings:
        $microsoft = "microsoft" nocase wide ascii
        $windows = "windows" nocase wide ascii
    condition:
        $microsoft or $windows
}
