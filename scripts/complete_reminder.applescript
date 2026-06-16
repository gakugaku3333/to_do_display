-- 引数: リマインダーID, "true" or "false", [候補リスト名 ...]
-- 候補リスト名を渡すとそれらだけを検索する（全リスト総当たりは iCloud 往復が重なり遅い）。
on run argv
    set reminderId to item 1 of argv
    set isCompleted to (item 2 of argv is "true")

    set targetLists to {}
    if (count of argv) ≥ 3 then
        repeat with i from 3 to (count of argv)
            set end of targetLists to item i of argv
        end repeat
    end if

    tell application "Reminders"
        if (count of targetLists) is 0 then
            set targetLists to name of every list
        end if
        repeat with listName in targetLists
            try
                set r to first reminder of list listName whose id is reminderId
                set completed of r to isCompleted
                return "ok"
            end try
        end repeat
    end tell
    return "not_found"
end run
