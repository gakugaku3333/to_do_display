-- 引数: リスト名
-- バッチ読み取りで高速化（個別プロパティアクセスを避ける）
on run argv
    set listName to item 1 of argv

    tell application "Reminders"
        set targetList to list listName
        set rems to reminders of targetList

        if (count of rems) is 0 then
            return "[]"
        end if

        -- バッチでプロパティを一括取得（iCloud往復を最小化）
        set remNames to name of every reminder in targetList
        set remDones to completed of every reminder in targetList
        set remIds to id of every reminder in targetList
        set remDueDates to due date of every reminder in targetList

        set jsonParts to {}
        set itemCount to count of rems

        repeat with i from 1 to itemCount
            set rName to item i of remNames
            set rDone to item i of remDones
            set rId to item i of remIds
            set rDueRaw to item i of remDueDates

            -- 期限日の整形
            set rDue to "null"
            if rDueRaw is not missing value then
                try
                    set y to year of rDueRaw
                    set m to month of rDueRaw as integer
                    set dd to day of rDueRaw

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
            end if

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
