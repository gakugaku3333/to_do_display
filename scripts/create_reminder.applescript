-- 引数: リスト名, タイトル, 本文(body), 期限(YYYY-MM-DD or "null")
on run argv
    set listName to item 1 of argv
    set reminderTitle to item 2 of argv
    set reminderBody to item 3 of argv
    set dueArg to item 4 of argv

    tell application "Reminders"
        try
            set targetList to list listName
        on error errMsg
            return "error: list not found: " & listName
        end try

        try
            if dueArg is "null" or dueArg is "" then
                set newReminder to make new reminder at targetList with properties {name:reminderTitle, body:reminderBody}
            else
                set dueDateObj to my parseDate(dueArg)
                set newReminder to make new reminder at targetList with properties {name:reminderTitle, body:reminderBody, due date:dueDateObj}
            end if
            return id of newReminder
        on error errMsg
            return "error: " & errMsg
        end try
    end tell
end run

-- YYYY-MM-DD 文字列を date オブジェクトに変換（時刻は 09:00 固定）
on parseDate(dateStr)
    set y to text 1 thru 4 of dateStr as integer
    set m to text 6 thru 7 of dateStr as integer
    set d to text 9 thru 10 of dateStr as integer

    set theDate to current date
    set time of theDate to 9 * hours
    set year of theDate to y
    set month of theDate to m
    set day of theDate to d
    return theDate
end parseDate
