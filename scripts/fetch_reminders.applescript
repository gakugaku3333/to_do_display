-- 引数: リスト名
on run argv
    set listName to item 1 of argv

    tell application "Reminders"
        set targetList to list listName
        set rems to reminders of targetList
        set jsonParts to {}

        repeat with r in rems
            set rName to name of r
            set rDone to completed of r
            set rId to id of r

            -- 期限日
            set rDue to "null"
            try
                set d to due date of r
                set y to year of d
                set m to month of d as integer
                set dd to day of d
                if m < 10 then
                    set ms to "0" & m
                else
                    set ms to m as text
                end if
                if dd < 10 then
                    set ds to "0" & dd
                else
                    set ds to dd as text
                end if
                set rDue to "\"" & (y as text) & "-" & ms & "-" & ds & "\""
            end try

            -- completed
            if rDone then
                set doneStr to "true"
            else
                set doneStr to "false"
            end if

            -- タイトル内のダブルクォートをエスケープ
            set cleanName to my replaceText(rName, "\"", "\\\"")

            -- JSON オブジェクト
            set jsonObj to "{\"id\":\"" & rId & "\","
            set jsonObj to jsonObj & "\"name\":\"" & cleanName & "\","
            set jsonObj to jsonObj & "\"completed\":" & doneStr & ","
            set jsonObj to jsonObj & "\"dueDate\":" & rDue & "}"

            set end of jsonParts to jsonObj
        end repeat

        set AppleScript's text item delimiters to ","
        set jsonArray to "[" & (jsonParts as text) & "]"
        set AppleScript's text item delimiters to ""
        return jsonArray
    end tell
end run

on replaceText(sourceText, searchStr, replaceStr)
    set AppleScript's text item delimiters to searchStr
    set theItems to every text item of sourceText
    set AppleScript's text item delimiters to replaceStr
    set sourceText to theItems as text
    set AppleScript's text item delimiters to ""
    return sourceText
end replaceText
