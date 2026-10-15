#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

/* No SetForegroundWindow, mouse injection or remote-memory writes. */
static void js(const wchar_t *s) {
    putchar('"');
    for (; *s; ++s) {
        unsigned c=*s;
        if (c=='"' || c=='\\') { putchar('\\'); putchar(c); }
        else if (c<32) printf("\\u%04x",c);
        else if (c<128) putchar(c);
        else {
            wchar_t pair[2]={*s,0}; int n=1; char b[8];
            if (c>=0xd800 && c<=0xdbff && s[1]>=0xdc00 && s[1]<=0xdfff) {pair[1]=*++s;n=2;}
            int z=WideCharToMultiByte(CP_UTF8,0,pair,n,b,sizeof b,NULL,NULL);
            fwrite(b,1,z,stdout);
        }
    }
    putchar('"');
}
static int fail(const char *s) {fprintf(stderr,"%s\n",s);return 2;}
static unsigned long long started(DWORD pid) {
    HANDLE p=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
    FILETIME c,e,k,u; if(!p)return 0;
    BOOL ok=GetProcessTimes(p,&c,&e,&k,&u);CloseHandle(p);
    return ok?((unsigned long long)c.dwHighDateTime<<32)|c.dwLowDateTime:0;
}
static BOOL msg(HWND w,UINT m,WPARAM a,LPARAM b,DWORD_PTR *r) {
    return SendMessageTimeoutW(w,m,a,b,SMTO_ABORTIFHUNG|SMTO_BLOCK,1500,r)!=0;
}
static BOOL secret(HWND w,const wchar_t *c) {
    return ((!_wcsicmp(c,L"Edit") || !_wcsnicmp(c,L"RichEdit",8)) &&
            (GetWindowLongPtrW(w,GWL_STYLE)&ES_PASSWORD));
}
static DWORD onlypid=0; static int first=1;
static BOOL CALLBACK item(HWND w,LPARAM unused) {
    (void)unused;
    DWORD pid;GetWindowThreadProcessId(w,&pid);
    if(onlypid && pid!=onlypid)return TRUE;
    wchar_t c[128]={0},t[2048]={0};DWORD_PTR r;
    GetClassNameW(w,c,128);BOOL redacted=secret(w,c);
    BOOL got=redacted?TRUE:msg(w,WM_GETTEXT,2048,(LPARAM)t,&r);
    RECT b={0};GetWindowRect(w,&b);
    if(!first)putchar(',');
    first=0;
    printf("{\"hwnd\":\"%llu\",\"pid\":%lu,\"started\":\"%llu\",\"parent\":\"%llu\",\"id\":%d,\"class\":",
       (unsigned long long)(uintptr_t)w,(unsigned long)pid,started(pid),
       (unsigned long long)(uintptr_t)GetParent(w),GetDlgCtrlID(w));
    js(c);printf(",\"visible\":%s,\"enabled\":%s,\"redacted\":%s,\"text_readable\":%s,\"rect\":[%ld,%ld,%ld,%ld],\"text\":",
       IsWindowVisible(w)?"true":"false",IsWindowEnabled(w)?"true":"false",
       redacted?"true":"false",got?"true":"false",b.left,b.top,b.right,b.bottom);
    js(redacted?L"[password]":t);putchar('}');return TRUE;
}
static BOOL CALLBACK top(HWND w,LPARAM unused) {
    if(IsWindowVisible(w)){item(w,unused);EnumChildWindows(w,item,unused);}return TRUE;
}
static void menus(HMENU m) {
    for(int i=0;m && i<GetMenuItemCount(m);i++) {
        wchar_t t[512]={0};GetMenuStringW(m,i,t,512,MF_BYPOSITION);
        if(!first)putchar(',');
        first=0;
        printf("{\"id\":%u,\"text\":",GetMenuItemID(m,i));js(t);putchar('}');
        menus(GetSubMenu(m,i));
    }
}
int wmain(int n,wchar_t **a) {
    if(n<2)return fail("command required");
    if(!wcscmp(a[1],L"snapshot")) {
        if(n>2)onlypid=wcstoul(a[2],NULL,10);
        putchar('[');EnumWindows(top,0);puts("]");return 0;
    }
    if(n<5)return fail("action requires HWND PID STARTED");
    HWND w=(HWND)(uintptr_t)_wcstoui64(a[2],NULL,10);
    DWORD pid=0,expected=wcstoul(a[3],NULL,10);GetWindowThreadProcessId(w,&pid);
    unsigned long long stamp=_wcstoui64(a[4],NULL,10);
    if(!IsWindow(w)||!expected||pid!=expected||!stamp||started(pid)!=stamp)
        return fail("stale HWND, wrong PID or wrong process creation timestamp");
    if(!IsWindowVisible(w)||!IsWindowEnabled(w))return fail("window is hidden or disabled");
    wchar_t c[128];GetClassNameW(w,c,128);DWORD_PTR r=0;
    if(!wcscmp(a[1],L"text")) {
        if(n!=6)return fail("text requires one value");
        if((_wcsicmp(c,L"Edit") && _wcsnicmp(c,L"RichEdit",8))||secret(w,c))
            return fail("text requires a non-password Edit/RichEdit control");
        if(!msg(w,WM_SETTEXT,0,(LPARAM)a[5],&r)||!r)return fail("WM_SETTEXT failed");
    } else if(!wcscmp(a[1],L"click")) {
        if(_wcsicmp(c,L"Button"))return fail("click requires a native Button");
        if(!msg(w,BM_CLICK,0,0,&r))return fail("BM_CLICK timed out");
    } else if(!wcscmp(a[1],L"select")) {
        if(n!=6||_wcsicmp(c,L"ComboBox"))return fail("select requires ComboBox and index");
        long i=wcstol(a[5],NULL,10);DWORD_PTR count;
        if(!msg(w,CB_GETCOUNT,0,0,&count)||i<0||i>=(long)count)return fail("invalid combo index");
        if(!msg(w,CB_SETCURSEL,i,0,&r)||(LRESULT)r==CB_ERR)return fail("selection failed");
        if(!msg(GetParent(w),WM_COMMAND,MAKEWPARAM(GetDlgCtrlID(w),CBN_SELCHANGE),(LPARAM)w,&r))return fail("notification timed out");
    } else if(!wcscmp(a[1],L"menu")) {
        putchar('[');menus(GetMenu(w));puts("]");return 0;
    } else if(!wcscmp(a[1],L"command")) {
        if(n!=6)return fail("command requires an observed menu ID");
        if(!PostMessageW(w,WM_COMMAND,wcstoul(a[5],NULL,10),0))return fail("command failed");
    } else if(!wcscmp(a[1],L"close")) {
        if(!PostMessageW(w,WM_CLOSE,0,0))return fail("close failed");
    } else return fail("unknown action");
    puts("{\"accepted\":true,\"verification_required\":true}");return 0;
}
