#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
static HWND edit,status,combo;static HFONT font;
static LRESULT CALLBACK proc(HWND w,UINT m,WPARAM a,LPARAM b){
    if(m==WM_CREATE){
        font=CreateFontW(-22,0,0,0,FW_NORMAL,0,0,0,DEFAULT_CHARSET,0,0,0,0,L"Arial");
        HWND title=CreateWindowW(L"STATIC",L"Windows app, controlled from Linux",WS_CHILD|WS_VISIBLE,28,26,670,34,w,0,0,0);
        edit=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"Ready for native Win32 input",WS_CHILD|WS_VISIBLE|ES_AUTOHSCROLL,28,84,670,44,w,(HMENU)101,0,0);
        combo=CreateWindowW(L"COMBOBOX",L"",WS_CHILD|WS_VISIBLE|CBS_DROPDOWNLIST,28,150,300,150,w,(HMENU)102,0,0);
        SendMessageW(combo,CB_ADDSTRING,0,(LPARAM)L"Before automation");SendMessageW(combo,CB_ADDSTRING,0,(LPARAM)L"Native control selected");SendMessageW(combo,CB_SETCURSEL,0,0);
        HWND button=CreateWindowW(L"BUTTON",L"Apply",WS_CHILD|WS_VISIBLE,370,150,150,44,w,(HMENU)103,0,0);
        status=CreateWindowW(L"STATIC",L"Waiting for verified input",WS_CHILD|WS_VISIBLE,28,224,670,80,w,(HMENU)104,0,0);
        HWND note=CreateWindowW(L"STATIC",L"Synthetic demo data only. No foreground activation.",WS_CHILD|WS_VISIBLE,28,318,670,60,w,0,0,0);
        CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"synthetic-password",WS_CHILD|WS_VISIBLE|ES_PASSWORD,28,390,300,28,w,(HMENU)105,0,0);
        HWND controls[]={title,edit,combo,button,status,note};for(int i=0;i<6;i++)SendMessageW(controls[i],WM_SETFONT,(WPARAM)font,TRUE);
    }
    if(m==WM_COMMAND&&LOWORD(a)==103){wchar_t t[1024];GetWindowTextW(edit,t,1024);SetWindowTextW(status,t);}
    if(m==WM_DESTROY){DeleteObject(font);PostQuitMessage(0);return 0;}
    return DefWindowProcW(w,m,a,b);
}
int WINAPI wWinMain(HINSTANCE h,HINSTANCE p,LPWSTR args,int show){
    (void)p;(void)args;(void)show;WNDCLASSW c={0};c.lpfnWndProc=proc;c.hInstance=h;c.lpszClassName=L"LinuxWindowsAppsDemo";c.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);c.hCursor=LoadCursorW(0,IDC_ARROW);RegisterClassW(&c);
    CreateWindowW(c.lpszClassName,L"linux-windows-apps | real Win32 demo",WS_OVERLAPPEDWINDOW|WS_VISIBLE,40,40,760,500,0,0,h,0);
    MSG m;while(GetMessageW(&m,0,0,0)>0){TranslateMessage(&m);DispatchMessageW(&m);}return 0;
}
