-- 引数: リマインダーID, "true" or "false"
on run argv
    set reminderId to item 1 of argv
    set isCompleted to (item 2 of argv is "true")

    tell application "Reminders"
        repeat with aList in every list
            try
                set r to first reminder of aList whose id is reminderId
                set completed of r to isCompleted
                return "ok"
            end try
        end repeat
    end tell
    return "not_found"
end run
